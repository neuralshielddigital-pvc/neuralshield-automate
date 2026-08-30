from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.billing import Payment, Plan, Subscription
from app.models.enums import SubscriptionStatus
from app.models.system import WebhookEvent
from app.models.user import User
from app.services.agency_commerce_service import AgencyCommerceService


class PaddleWebhookService:
    SIGNATURE_TOLERANCE_SECONDS = 300

    def __init__(self, db: Session) -> None:
        self.db = db

    def handle_webhook_event(
        self,
        payload: bytes,
        signature: str | None,
    ) -> dict[str, Any]:
        self._verify_signature(payload, signature)

        try:
            event = json.loads(payload)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Paddle webhook payload.",
            ) from exc

        if not isinstance(event, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Paddle webhook payload.",
            )

        remote_event_id = str(event.get("event_id") or "").strip()
        event_type = str(event.get("event_type") or "").strip()

        if not remote_event_id.startswith("evt_"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Paddle event identifier is missing or invalid.",
            )

        if not event_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Paddle event type is missing.",
            )

        event_id = f"paddle:{remote_event_id}"

        existing = (
            self.db.query(WebhookEvent)
            .filter(WebhookEvent.event_id == event_id)
            .first()
        )

        if existing is not None and existing.processed:
            return {
                "received": True,
                "processed": True,
                "duplicate": True,
                "event_id": event_id,
                "event_type": event_type,
            }

        if existing is None:
            self.db.add(
                WebhookEvent(
                    event_id=event_id,
                    type=event_type,
                    payload=event,
                    processed=False,
                )
            )
            try:
                self.db.commit()
            except IntegrityError:
                self.db.rollback()

        handled = self._dispatch_webhook(event_type, event)

        record = (
            self.db.query(WebhookEvent)
            .filter(WebhookEvent.event_id == event_id)
            .first()
        )

        if record is not None:
            record.processed = True

        self.db.commit()

        return {
            "received": True,
            "processed": True,
            "handled": handled,
            "event_id": event_id,
            "event_type": event_type,
        }

    def _verify_signature(
        self,
        payload: bytes,
        signature: str | None,
    ) -> None:
        secret = str(settings.PADDLE_WEBHOOK_SECRET or "").strip()

        if not secret:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Paddle webhook secret is not configured.",
            )

        if not signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing Paddle-Signature header.",
            )

        timestamp, signatures = self._parse_signature_header(signature)

        current_timestamp = int(time.time())
        if abs(current_timestamp - timestamp) > self.SIGNATURE_TOLERANCE_SECONDS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Paddle webhook signature has expired.",
            )

        signed_payload = (
            str(timestamp).encode("utf-8")
            + b":"
            + payload
        )

        expected = hmac.new(
            secret.encode("utf-8"),
            signed_payload,
            hashlib.sha256,
        ).hexdigest()

        if not any(
            hmac.compare_digest(expected, candidate)
            for candidate in signatures
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Paddle webhook signature.",
            )

    @staticmethod
    def _parse_signature_header(
        signature: str,
    ) -> tuple[int, list[str]]:
        timestamp: int | None = None
        signatures: list[str] = []

        for component in signature.split(";"):
            key, separator, value = component.strip().partition("=")

            if not separator:
                continue

            if key == "ts":
                try:
                    timestamp = int(value)
                except ValueError as exc:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid Paddle signature timestamp.",
                    ) from exc
            elif key == "h1" and value:
                signatures.append(value)

        if timestamp is None or not signatures:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Paddle-Signature header.",
            )

        return timestamp, signatures

    def _dispatch_webhook(
        self,
        event_type: str,
        event: dict[str, Any],
    ) -> bool:
        subscription_events = {
            "subscription.created",
            "subscription.updated",
            "subscription.activated",
            "subscription.canceled",
            "subscription.paused",
            "subscription.resumed",
            "subscription.past_due",
        }

        transaction_events = {
            "transaction.completed",
            "transaction.payment_failed",
            "transaction.past_due",
            "transaction.canceled",
        }

        if event_type in subscription_events:
            self._handle_subscription_event(event_type, event)
            return True

        if event_type in transaction_events:
            self._handle_transaction_event(event_type, event)
            return True

        return False

    def _handle_subscription_event(
        self,
        event_type: str,
        event: dict[str, Any],
    ) -> None:
        data = event.get("data") or {}

        if not isinstance(data, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Paddle subscription payload.",
            )

        provider_subscription_id = str(data.get("id") or "").strip()
        customer_id = str(data.get("customer_id") or "").strip()

        if not provider_subscription_id.startswith("sub_"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Paddle subscription identifier is invalid.",
            )

        if not customer_id.startswith("ctm_"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Paddle customer identifier is invalid.",
            )

        user, tenant_id = self._account_context(data)
        plan = self._plan_from_event(data)

        remote_status = str(data.get("status") or "").strip().lower()
        local_status = self._subscription_status(
            event_type,
            remote_status,
        )

        billing_period = data.get("current_billing_period") or {}
        scheduled_change = data.get("scheduled_change") or {}

        period_start = self._parse_datetime(
            billing_period.get("starts_at")
        )
        period_end = self._parse_datetime(
            billing_period.get("ends_at")
        )

        cancel_at_period_end = (
            str(scheduled_change.get("action") or "").lower()
            == "cancel"
        )

        provider_key = f"paddle:{provider_subscription_id}"

        subscription = (
            self.db.query(Subscription)
            .filter(
                Subscription.stripe_subscription_id
                == provider_key
            )
            .first()
        )

        if subscription is None:
            subscription = Subscription(
                user_id=user.id,
                tenant_id=tenant_id,
                plan_id=plan.id,
                stripe_customer_id=f"paddle:{customer_id}",
                stripe_subscription_id=provider_key,
                status=local_status,
                current_period_start=period_start,
                current_period_end=period_end,
                cancel_at_period_end=cancel_at_period_end,
            )
            self.db.add(subscription)
            return

        if (
            subscription.user_id != user.id
            or subscription.tenant_id != tenant_id
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Paddle subscription is associated "
                    "with another account."
                ),
            )

        subscription.plan_id = plan.id
        subscription.stripe_customer_id = f"paddle:{customer_id}"
        subscription.status = local_status
        subscription.current_period_start = period_start
        subscription.current_period_end = period_end
        subscription.cancel_at_period_end = cancel_at_period_end

    def _handle_transaction_event(
        self,
        event_type: str,
        event: dict[str, Any],
    ) -> None:
        data = event.get("data") or {}

        if not isinstance(data, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Paddle transaction payload.",
            )

        if event_type == "transaction.completed":
            agency_service = AgencyCommerceService(self.db)

            if agency_service.is_agency_transaction(data):
                agency_service.handle_completed_transaction(data)
                return

        transaction_id = str(data.get("id") or "").strip()

        if not transaction_id.startswith("txn_"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Paddle transaction identifier is invalid.",
            )

        user, tenant_id = self._account_context(data)
        plan = self._plan_from_event(data)

        subscription_id = str(
            data.get("subscription_id") or ""
        ).strip()

        if subscription_id and not subscription_id.startswith("sub_"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Paddle transaction subscription "
                    "identifier is invalid."
                ),
            )

        amount, currency = self._transaction_amount(data)
        payment_status = self._transaction_status(
            event_type,
            str(data.get("status") or "").strip().lower(),
        )

        provider_payment_id = (
            f"paddle:transaction:{transaction_id}"
        )

        payment = (
            self.db.query(Payment)
            .filter(
                Payment.provider_payment_id
                == provider_payment_id
            )
            .first()
        )

        if payment is None:
            payment = Payment(
                user_id=user.id,
                tenant_id=tenant_id,
                plan_id=plan.id,
                provider="paddle",
                provider_payment_id=provider_payment_id,
                provider_order_id=(
                    f"paddle:{subscription_id}"
                    if subscription_id
                    else transaction_id
                ),
                amount=amount,
                currency=currency,
                status=payment_status,
            )
            self.db.add(payment)
        else:
            if (
                payment.user_id != user.id
                or payment.tenant_id != tenant_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Paddle transaction is associated "
                        "with another account."
                    ),
                )

            payment.plan_id = plan.id
            payment.amount = amount
            payment.currency = currency
            payment.status = payment_status

        if subscription_id:
            subscription = (
                self.db.query(Subscription)
                .filter(
                    Subscription.stripe_subscription_id
                    == f"paddle:{subscription_id}"
                )
                .first()
            )

            if subscription is not None:
                if (
                    subscription.user_id != user.id
                    or subscription.tenant_id != tenant_id
                ):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            "Paddle transaction subscription "
                            "belongs to another account."
                        ),
                    )

                if payment_status == "paid":
                    subscription.status = (
                        SubscriptionStatus.ACTIVE
                    )
                elif payment_status in {
                    "failed",
                    "past_due",
                }:
                    subscription.status = (
                        SubscriptionStatus.INCOMPLETE
                    )

    @staticmethod
    def _transaction_amount(
        data: dict[str, Any],
    ) -> tuple[Decimal, str]:
        details = data.get("details") or {}
        totals = details.get("totals") or {}

        amount_value = (
            totals.get("grand_total")
            or totals.get("total")
            or data.get("grand_total")
        )

        try:
            amount_minor = int(amount_value)
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Paddle transaction amount is invalid.",
            ) from exc

        if amount_minor < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Paddle transaction amount is invalid.",
            )

        currency = str(
            data.get("currency_code") or ""
        ).strip().upper()

        if currency != "USD":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Paddle transaction currency must be USD.",
            )

        return (
            Decimal(amount_minor) / Decimal("100"),
            currency,
        )

    @staticmethod
    def _transaction_status(
        event_type: str,
        remote_status: str,
    ) -> str:
        if (
            event_type == "transaction.completed"
            or remote_status == "completed"
        ):
            return "paid"

        if event_type == "transaction.payment_failed":
            return "failed"

        if (
            event_type == "transaction.past_due"
            or remote_status == "past_due"
        ):
            return "past_due"

        if (
            event_type == "transaction.canceled"
            or remote_status == "canceled"
        ):
            return "canceled"

        return remote_status or "pending"

    def _account_context(
        self,
        data: dict[str, Any],
    ) -> tuple[User, UUID]:
        custom_data = data.get("custom_data") or {}

        if not isinstance(custom_data, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Paddle custom data is invalid.",
            )

        user_id = self._parse_uuid(
            custom_data.get("user_id"),
            "user",
        )
        tenant_id = self._parse_uuid(
            custom_data.get("tenant_id"),
            "tenant",
        )

        user = self.db.get(User, user_id)

        if user is None or user.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Paddle webhook account was not found.",
            )

        return user, tenant_id

    def _plan_from_event(
        self,
        data: dict[str, Any],
    ) -> Plan:
        items = data.get("items") or []

        if not isinstance(items, list) or not items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Paddle webhook has no billing items.",
            )

        first_item = items[0] or {}
        price = first_item.get("price") or {}
        price_id = str(
            price.get("id")
            or first_item.get("price_id")
            or ""
        ).strip()

        return self._plan_for_price(price_id)

    def _plan_for_price(
        self,
        price_id: str,
    ) -> Plan:
        mapping = {
            str(settings.PADDLE_STARTER_PRICE_ID): "Starter",
            str(settings.PADDLE_PRO_PRICE_ID): "Pro",
            str(settings.PADDLE_BUSINESS_PRICE_ID): "Enterprise",
        }

        local_name = mapping.get(price_id)

        if local_name is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Paddle price is not an approved plan.",
            )

        plan = (
            self.db.query(Plan)
            .filter(Plan.name == local_name)
            .order_by(Plan.created_at.desc())
            .first()
        )

        if plan is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Paddle billing plan was not found.",
            )

        return plan

    @staticmethod
    def _subscription_status(
        event_type: str,
        remote_status: str,
    ) -> SubscriptionStatus:
        if (
            event_type == "subscription.canceled"
            or remote_status == "canceled"
        ):
            return SubscriptionStatus.CANCELED

        if (
            event_type == "subscription.paused"
            or remote_status == "paused"
        ):
            return SubscriptionStatus.PAUSED

        if (
            event_type == "subscription.past_due"
            or remote_status == "past_due"
        ):
            return SubscriptionStatus.INCOMPLETE

        if remote_status in {
            "active",
            "trialing",
        }:
            return SubscriptionStatus.ACTIVE

        if event_type in {
            "subscription.created",
            "subscription.activated",
            "subscription.resumed",
        }:
            return SubscriptionStatus.ACTIVE

        return SubscriptionStatus.INCOMPLETE

    @staticmethod
    def _parse_uuid(
        value: Any,
        label: str,
    ) -> UUID:
        try:
            return UUID(str(value))
        except (TypeError, ValueError, AttributeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Paddle webhook {label} identifier is invalid.",
            ) from exc

    @staticmethod
    def _parse_datetime(
        value: Any,
    ) -> datetime | None:
        if not value:
            return None

        try:
            return datetime.fromisoformat(
                str(value).replace("Z", "+00:00")
            )
        except ValueError:
            return None
