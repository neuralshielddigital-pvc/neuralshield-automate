"""Persist *independently verified* Whop Agency purchases transactionally.

This service is NOT an HTTP endpoint. The production caller must first
authenticate the provider webhook, independently fetch the purchase from
Whop using server credentials, and pass a VerifiedAgencyPurchase produced
by prepare_verified_whop_purchase. Never call this with browser data.
"""
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.agency_commerce import (
    AgencyCustomer, AgencyEntitlement, AgencyFulfilment, AgencyOrder,
)
from app.services.agency_whop_contract import VerifiedAgencyPurchase
from app.services.agency_whop_fulfillment_policy import decide_whop_fulfillment


class AgencyWhopPersistence:
    def __init__(self, db: Session) -> None:
        self.db = db

    def record_verified_purchase(self, purchase: VerifiedAgencyPurchase) -> dict:
        # Verify against explicit trusted contract; never blindly cast webhook data.
        if not isinstance(purchase, VerifiedAgencyPurchase) or purchase.provider != "whop":
            raise ValueError("Verified Whop purchase required")
        if not purchase.provider_order_id or not purchase.customer_email:
            raise ValueError("Missing purchase identity")
        try:
            # Row-level lock protects existing identity, DB uniqueness protects races.
            existing = (
                self.db.query(AgencyOrder)
                .filter(
                    AgencyOrder.payment_provider == "whop",
                    AgencyOrder.provider_order_id == purchase.provider_order_id,
                ).with_for_update().first()
            )
            decision = decide_whop_fulfillment(
                purchase,
                existing_order_provider=existing.payment_provider if existing else None,
                existing_order_id=existing.provider_order_id if existing else None,
                existing_order_product_key=existing.product_key if existing else None,
            )
            if decision.action == "duplicate":
                return {"handled": True, "duplicate": True, "order_id": str(existing.id)}
            if decision.action != "grant":
                raise ValueError("Whop purchase identity conflict")

            customer = (
                self.db.query(AgencyCustomer)
                .filter(AgencyCustomer.email == purchase.customer_email)
                .with_for_update()
                .first()
            )
            if customer is None:
                customer = AgencyCustomer(email=purchase.customer_email, status="active")
                self.db.add(customer)
                self.db.flush()
            order = AgencyOrder(
                customer_id=customer.id,
                payment_provider="whop",
                provider_order_id=purchase.provider_order_id,
                provider_product_id=purchase.provider_product_id,
                paddle_transaction_id=None,
                paddle_price_id=None,
                product_key=purchase.product_key,
                amount=purchase.amount,
                currency=purchase.currency,
                status="completed",
                completed_at=datetime.now(timezone.utc),
            )
            self.db.add(order)
            self.db.flush()
            entitlement = AgencyEntitlement(
                customer_id=customer.id, order_id=order.id,
                product_key=purchase.product_key,
                status="active", granted_at=datetime.now(timezone.utc),
            )
            self.db.add(entitlement)
            self.db.flush()
            self.db.add(AgencyFulfilment(
                entitlement_id=entitlement.id,
                status="pending",
                delivery_method="member_portal",
                destination=customer.email,
            ))
            self.db.commit()
            return {"handled": True, "duplicate": False, "order_id": str(order.id)}
        except IntegrityError:
            # Concurrent same-order delivery must not leave a partially committed grant.
            self.db.rollback()
            raise
        except Exception:
            self.db.rollback()
            raise
