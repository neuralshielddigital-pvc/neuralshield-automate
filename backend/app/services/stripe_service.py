from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

import stripe
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.billing import Plan, Subscription
from app.models.enums import PlanInterval, SubscriptionStatus
from app.models.system import WebhookEvent
from app.models.user import User
from app.services.affiliate_service import AffiliateService


logger = logging.getLogger(__name__)


class StripeService:
    def __init__(self, db: Session) -> None:
        self.db = db
        stripe.api_key = settings.STRIPE_SECRET_KEY
        stripe.api_version = "2026-02-25.clover"

    def get_price_id(self, plan_name: str) -> str:
        normalized = self._normalize_plan_name(plan_name)
        price_ids = {
            "starter": settings.STRIPE_STARTER_PRICE_ID,
            "pro": settings.STRIPE_PRO_PRICE_ID,
            "enterprise": settings.STRIPE_ENTERPRISE_PRICE_ID,
        }
        price_id = price_ids.get(normalized)
        if price_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid plan name. Choose Starter, Pro, or Enterprise.",
            )
        if not price_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Stripe price ID is not configured for {plan_name}.",
            )
        return price_id

    def create_checkout_session(self, user: User, plan_name: str) -> dict[str, str]:
        self._ensure_stripe_configured()
        price_id = self.get_price_id(plan_name)
        customer_id = self._get_or_create_customer(user)

        try:
            checkout_session = stripe.checkout.Session.create(
                mode="subscription",
                customer=customer_id,
                line_items=[{"price": price_id, "quantity": 1}],
                success_url=settings.FRONTEND_SUCCESS_URL,
                cancel_url=settings.FRONTEND_CANCEL_URL,
                client_reference_id=str(user.id),
                metadata={
                    "user_id": str(user.id),
                    "tenant_id": str(user.tenant_id),
                    "plan_name": self._canonical_plan_name(plan_name),
                },
                subscription_data={
                    "metadata": {
                        "user_id": str(user.id),
                        "tenant_id": str(user.tenant_id),
                        "plan_name": self._canonical_plan_name(plan_name),
                    }
                },
            )
        except stripe.error.StripeError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Stripe checkout session could not be created: {exc.user_message or str(exc)}",
            ) from exc

        if checkout_session.url is None:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Stripe did not return a checkout URL.",
            )
        return {"checkout_url": checkout_session.url}

    def create_billing_portal_session(self, user: User) -> dict[str, str]:
        self._ensure_stripe_configured()
        customer_id = self._get_or_create_customer(user)

        try:
            portal_session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=settings.FRONTEND_SUCCESS_URL,
            )
        except stripe.error.StripeError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Stripe billing portal session could not be created: {exc.user_message or str(exc)}",
            ) from exc

        return {"portal_url": portal_session.url}

    def get_current_subscription(self, user: User) -> Subscription | None:
        return self.db.scalar(
            select(Subscription)
            .options(selectinload(Subscription.plan))
            .where(Subscription.user_id == user.id, Subscription.tenant_id == user.tenant_id)
            .order_by(Subscription.created_at.desc())
        )

    def handle_webhook_event(self, payload: bytes, signature: str | None) -> dict[str, Any]:
        if not settings.STRIPE_WEBHOOK_SECRET:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stripe webhook secret is not configured.",
            )
        if not signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing Stripe-Signature header.",
            )

        try:
            event = stripe.Webhook.construct_event(
                payload=payload,
                sig_header=signature,
                secret=settings.STRIPE_WEBHOOK_SECRET,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Stripe webhook payload.",
            ) from exc
        except stripe.error.SignatureVerificationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Stripe webhook signature.",
            ) from exc

        event_id = event["id"]
        event_type = event["type"]
        event_payload = event.to_dict_recursive() if hasattr(event, "to_dict_recursive") else dict(event)

        existing = self.db.scalar(select(WebhookEvent).where(WebhookEvent.event_id == event_id))
        if existing is not None and existing.processed:
            logger.info("Skipping already processed Stripe webhook event %s (%s)", event_id, event_type)
            return {"received": True, "processed": True, "event_id": event_id}

        if existing is None:
            webhook_event = WebhookEvent(
                event_id=event_id,
                type=event_type,
                payload=event_payload,
                processed=False,
            )
            self.db.add(webhook_event)
            try:
                self.db.commit()
            except IntegrityError:
                self.db.rollback()
                existing = self.db.scalar(select(WebhookEvent).where(WebhookEvent.event_id == event_id))
                if existing is not None and existing.processed:
                    logger.info("Skipping concurrently processed Stripe webhook event %s (%s)", event_id, event_type)
                    return {"received": True, "processed": True, "event_id": event_id}
        else:
            logger.info("Retrying unprocessed Stripe webhook event %s (%s)", event_id, event_type)

        try:
            logger.info("Processing Stripe webhook event %s (%s)", event_id, event_type)
            self._dispatch_webhook(event)
            webhook_event = self.db.scalar(select(WebhookEvent).where(WebhookEvent.event_id == event_id))
            if webhook_event is not None:
                webhook_event.processed = True
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return {"received": True, "processed": True, "event_id": event_id}

    def _dispatch_webhook(self, event: stripe.Event) -> None:
        event_type = event["type"]
        data_object = event["data"]["object"]

        if event_type == "checkout.session.completed":
            self._handle_checkout_completed(data_object)
        elif event_type in {
            "customer.subscription.created",
            "customer.subscription.updated",
        }:
            self._upsert_subscription_from_stripe_subscription(data_object)
        elif event_type == "customer.subscription.deleted":
            self._mark_subscription_canceled(data_object)
        elif event_type == "invoice.payment_succeeded":
            self._handle_invoice_payment_succeeded(data_object)
        elif event_type == "invoice.payment_failed":
            self._handle_invoice_payment_failed(data_object)

    def _handle_checkout_completed(self, session: dict[str, Any]) -> None:
        subscription_id = session.get("subscription")
        if not subscription_id:
            return
        subscription = stripe.Subscription.retrieve(subscription_id)
        self._upsert_subscription_from_stripe_subscription(
            subscription,
            fallback_user_id=session.get("metadata", {}).get("user_id") or session.get("client_reference_id"),
            fallback_tenant_id=session.get("metadata", {}).get("tenant_id"),
            fallback_customer_id=session.get("customer"),
        )

    def _handle_invoice_payment_succeeded(self, invoice: dict[str, Any]) -> None:
        subscription_id = invoice.get("subscription")
        if not subscription_id:
            return
        subscription = stripe.Subscription.retrieve(subscription_id)
        self._upsert_subscription_from_stripe_subscription(subscription)

    def _handle_invoice_payment_failed(self, invoice: dict[str, Any]) -> None:
        subscription_id = invoice.get("subscription")
        if not subscription_id:
            return

        local_subscription = self.db.scalar(
            select(Subscription).where(Subscription.stripe_subscription_id == subscription_id)
        )
        if local_subscription is not None:
            local_subscription.status = SubscriptionStatus.PAST_DUE
            return

        stripe_subscription = stripe.Subscription.retrieve(subscription_id)
        self._upsert_subscription_from_stripe_subscription(stripe_subscription)
        local_subscription = self.db.scalar(
            select(Subscription).where(Subscription.stripe_subscription_id == subscription_id)
        )
        if local_subscription is not None:
            local_subscription.status = SubscriptionStatus.PAST_DUE

    def _upsert_subscription_from_stripe_subscription(
        self,
        stripe_subscription: dict[str, Any],
        fallback_user_id: str | None = None,
        fallback_tenant_id: str | None = None,
        fallback_customer_id: str | None = None,
    ) -> None:
        subscription_id = self._stripe_get(stripe_subscription, "id")
        customer_id = self._stripe_get(stripe_subscription, "customer") or fallback_customer_id
        if not subscription_id or not customer_id:
            return

        metadata = self._stripe_get(stripe_subscription, "metadata", {}) or {}
        user_id = self._stripe_get(metadata, "user_id") or fallback_user_id
        tenant_id = self._stripe_get(metadata, "tenant_id") or fallback_tenant_id

        user = self._resolve_user_for_subscription(customer_id, user_id)
        if user is None:
            return
        try:
            resolved_tenant_id = UUID(tenant_id) if tenant_id else user.tenant_id
        except ValueError:
            resolved_tenant_id = user.tenant_id

        plan = self._resolve_plan_for_subscription(stripe_subscription)
        current_period_start, current_period_end = self._subscription_period(stripe_subscription)
        logger.info(
            "Stripe subscription %s final saved datetime candidates: current_period_start=%s current_period_end=%s",
            subscription_id,
            current_period_start,
            current_period_end,
        )
        subscription = self.db.scalar(
            select(Subscription).where(Subscription.stripe_subscription_id == subscription_id)
        )

        if subscription is None:
            subscription = Subscription(
                user_id=user.id,
                tenant_id=resolved_tenant_id,
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                plan_id=plan.id,
                status=self._map_subscription_status(self._stripe_get(stripe_subscription, "status")),
                current_period_start=current_period_start,
                current_period_end=current_period_end,
                cancel_at_period_end=bool(self._stripe_get(stripe_subscription, "cancel_at_period_end", False)),
            )
            self.db.add(subscription)
        else:
            subscription.user_id = user.id
            subscription.tenant_id = resolved_tenant_id
            subscription.stripe_customer_id = customer_id
            subscription.plan_id = plan.id
            subscription.status = self._map_subscription_status(self._stripe_get(stripe_subscription, "status"))
            subscription.current_period_start = current_period_start
            subscription.current_period_end = current_period_end
            subscription.cancel_at_period_end = bool(self._stripe_get(stripe_subscription, "cancel_at_period_end", False))

        logger.info(
            "Saved subscription period values for Stripe subscription %s: current_period_start=%s current_period_end=%s",
            subscription_id,
            current_period_start,
            current_period_end,
        )

        if subscription.status == SubscriptionStatus.ACTIVE:
            AffiliateService(self.db).create_commission_for_active_subscription(user, plan.price)

        if user.stripe_customer_id != customer_id:
            user.stripe_customer_id = customer_id

    def _mark_subscription_canceled(self, stripe_subscription: dict[str, Any]) -> None:
        subscription_id = self._stripe_get(stripe_subscription, "id")
        if not subscription_id:
            return
        subscription = self.db.scalar(
            select(Subscription).where(Subscription.stripe_subscription_id == subscription_id)
        )
        if subscription is not None:
            current_period_start, current_period_end = self._subscription_period(stripe_subscription)
            subscription.status = SubscriptionStatus.CANCELED
            subscription.cancel_at_period_end = bool(self._stripe_get(stripe_subscription, "cancel_at_period_end", False))
            subscription.current_period_start = current_period_start
            subscription.current_period_end = current_period_end
            logger.info(
                "Saved canceled subscription period values for Stripe subscription %s: current_period_start=%s current_period_end=%s",
                subscription_id,
                current_period_start,
                current_period_end,
            )

    def _get_or_create_customer(self, user: User) -> str:
        if user.stripe_customer_id:
            return user.stripe_customer_id

        try:
            customer = stripe.Customer.create(
                email=user.email,
                metadata={
                    "user_id": str(user.id),
                    "tenant_id": str(user.tenant_id),
                },
            )
        except stripe.error.StripeError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Stripe customer could not be created: {exc.user_message or str(exc)}",
            ) from exc

        user.stripe_customer_id = customer.id
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return customer.id

    def _resolve_user_for_subscription(self, customer_id: str, user_id: str | None) -> User | None:
        if user_id:
            try:
                user = self.db.get(User, UUID(user_id))
                if user is not None:
                    return user
            except ValueError:
                logger.warning("Stripe webhook contained invalid user_id metadata: %s", user_id)
        return self.db.scalar(select(User).where(User.stripe_customer_id == customer_id))

    def _resolve_plan_for_subscription(self, stripe_subscription: dict[str, Any]) -> Plan:
        item = self._first_subscription_item(stripe_subscription)
        price = item.get("price") if item else None
        price_id = price.get("id") if price else None
        if not price_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Stripe subscription does not contain a price ID.",
            )

        plan = self.db.scalar(select(Plan).where(Plan.stripe_price_id == price_id))
        if plan is not None:
            return plan

        plan_name = self._plan_name_from_price_id(price_id)
        amount_cents = price.get("unit_amount") or 0
        recurring = price.get("recurring") or {}
        interval = PlanInterval.yearly if recurring.get("interval") == "year" else PlanInterval.monthly

        plan = Plan(
            name=plan_name,
            stripe_price_id=price_id,
            price=Decimal(amount_cents) / Decimal(100),
            interval=interval,
        )
        self.db.add(plan)
        self.db.flush()
        return plan

    def _first_subscription_item(self, stripe_subscription: dict[str, Any]) -> Any | None:
        items_container = self._stripe_get(stripe_subscription, "items", {})
        items = self._stripe_get(items_container, "data", [])
        if not items:
            return None
        return items[0]

    def _plan_name_from_price_id(self, price_id: str) -> str:
        mapping = {
            settings.STRIPE_STARTER_PRICE_ID: "Starter",
            settings.STRIPE_PRO_PRICE_ID: "Pro",
            settings.STRIPE_ENTERPRISE_PRICE_ID: "Enterprise",
        }
        return mapping.get(price_id, "Custom")

    def _map_subscription_status(self, stripe_status: str | None) -> SubscriptionStatus:
        if stripe_status in {"active", "trialing"}:
            return SubscriptionStatus.ACTIVE
        if stripe_status == "canceled":
            return SubscriptionStatus.CANCELED
        if stripe_status in {"past_due", "unpaid"}:
            return SubscriptionStatus.PAST_DUE
        return SubscriptionStatus.INCOMPLETE

    def _subscription_period(self, stripe_subscription: dict[str, Any]) -> tuple[datetime | None, datetime | None]:
        subscription_id = self._stripe_get(stripe_subscription, "id")
        item = self._first_subscription_item(stripe_subscription)

        logger.info(
            "Debug Stripe subscription period extraction: subscription_id=%s object_type=%s top_start_exists=%s top_end_exists=%s item_start_exists=%s item_end_exists=%s",
            subscription_id,
            type(stripe_subscription).__name__,
            self._stripe_field_exists(stripe_subscription, "current_period_start"),
            self._stripe_field_exists(stripe_subscription, "current_period_end"),
            self._stripe_field_exists(item, "current_period_start"),
            self._stripe_field_exists(item, "current_period_end"),
        )

        period_start = getattr(stripe_subscription, "current_period_start", None)
        period_end = getattr(stripe_subscription, "current_period_end", None)

        if period_start is None:
            period_start = self._stripe_item_get(stripe_subscription, "current_period_start")
        if period_end is None:
            period_end = self._stripe_item_get(stripe_subscription, "current_period_end")

        if item is not None:
            if period_start is None:
                period_start = getattr(item, "current_period_start", None)
            if period_end is None:
                period_end = getattr(item, "current_period_end", None)
            if period_start is None:
                period_start = self._stripe_item_get(item, "current_period_start")
            if period_end is None:
                period_end = self._stripe_item_get(item, "current_period_end")

        logger.info(
            "Extracted Stripe subscription %s final raw period timestamps: start_ts=%s end_ts=%s",
            subscription_id,
            period_start,
            period_end,
        )
        return self._from_unix(period_start), self._from_unix(period_end)

    def _from_unix(self, value: int | float | str | None) -> datetime | None:
        if value is None:
            return None
        return datetime.fromtimestamp(int(value), timezone.utc)

    def _stripe_get(self, stripe_object: Any, key: str, default: Any = None) -> Any:
        if stripe_object is None:
            return default
        if isinstance(stripe_object, dict):
            return stripe_object.get(key, default)
        try:
            value = stripe_object.get(key, default)
        except AttributeError:
            value = getattr(stripe_object, key, default)
        return default if value is None else value

    def _stripe_item_get(self, stripe_object: Any, key: str) -> Any:
        try:
            return stripe_object[key]
        except (KeyError, TypeError):
            return None

    def _stripe_field_exists(self, stripe_object: Any, key: str) -> bool:
        if stripe_object is None:
            return False
        if getattr(stripe_object, key, None) is not None:
            return True
        return self._stripe_item_get(stripe_object, key) is not None

    def _normalize_plan_name(self, plan_name: str) -> str:
        return plan_name.strip().lower()

    def _canonical_plan_name(self, plan_name: str) -> str:
        normalized = self._normalize_plan_name(plan_name)
        return {
            "starter": "Starter",
            "pro": "Pro",
            "enterprise": "Enterprise",
        }.get(normalized, plan_name.strip())

    def _ensure_stripe_configured(self) -> None:
        if not settings.STRIPE_SECRET_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stripe secret key is not configured.",
            )
