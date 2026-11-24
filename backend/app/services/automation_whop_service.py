"""Application-session-owned hosted checkout and provider-verified paid access.

No email match, browser receipt, webhook payload or arbitrary membership claim
can select a beneficiary. Only a previously persisted, authenticated intent can.
Transactions belong to the caller except checkout's durable pre-provider intent.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4
import hashlib

import httpx
from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.automation_whop import AutomationWhopIntent as Intent, AutomationWhopMembership as Membership, AutomationWhopPayment as Receipt
from app.models.billing import Plan, Subscription, Payment
from app.models.enums import PlanInterval, SubscriptionStatus
from app.models.user import User
from app.services.automation_whop_catalog import VERSION, LOCAL_NAMES, plan_for, binding_for
from app.services.automation_whop_contract import CheckoutIntent, TenantContext
from app.services.automation_whop_transport import WhopAdapter, WhopSettings, WhopError, identifier, object_value, provider_timestamp

UTC = timezone.utc
SNAPSHOT_TTL = timedelta(minutes=10)


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def paid_now(row: Membership, now: datetime) -> bool:
    return bool(row.active and not row.terminal and row.current_period_start and row.current_period_end
                and utc(row.current_period_start) <= now < utc(row.current_period_end)
                and timedelta(0) <= now - utc(row.checked_at) <= SNAPSHOT_TTL)


def lock_user(db: Session, user_id: UUID) -> None:
    # Cross-process serialization; row locks alone do not lock an absent intent.
    if db.get_bind().dialect.name == "postgresql":
        key = int.from_bytes(hashlib.sha256(str(user_id).encode()).digest()[:8], "big", signed=True)
        db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})


def owned_memberships(db: Session, user: User) -> list[Membership]:
    return list(db.scalars(select(Membership).where(Membership.user_id == user.id, Membership.tenant_id == user.tenant_id)))


def effective_membership(db: Session, user: User, now: datetime | None = None) -> Membership | None:
    active = [row for row in owned_memberships(db, user) if paid_now(row, now or datetime.now(UTC))]
    if len(active) > 1:
        raise HTTPException(409, "Multiple subscriptions require support review.")
    return active[0] if active else None


def contract(row: Intent) -> CheckoutIntent:
    plan = plan_for(row.plan_code)
    if row.catalog_version != VERSION or row.amount_minor != plan.amount_minor:
        raise WhopError("persisted_catalog_mismatch")
    return CheckoutIntent(str(row.id), str(row.tenant_id), plan, str(row.id))


def adapter(client: httpx.Client) -> WhopAdapter:
    return WhopAdapter(WhopSettings(settings.AUTOMATION_WHOP_ACCOUNT_ID,
                                   settings.AUTOMATION_WHOP_API_KEY,
                                   environment="production", enabled=settings.AUTOMATION_WHOP_ENABLED), client)


class AutomationWhopService:
    def __init__(self, db: Session, provider: WhopAdapter):
        self.db, self.provider = db, provider

    def checkout(self, user: User, code: str, command: UUID) -> dict:
        self.provider.settings.require_enabled()
        if not user.is_active or not user.tenant_id:
            raise HTTPException(403, "An active account is required.")
        if not user.email_verified_at:
            raise HTTPException(403, "Verify your email before subscribing.")
        plan = plan_for(code.lower())
        lock_user(self.db, user.id)
        legacy = self.db.scalars(select(Subscription).where(Subscription.user_id == user.id,
            Subscription.tenant_id == user.tenant_id, Subscription.status == SubscriptionStatus.ACTIVE)).all()
        # Preserve manual/legacy access and prevent accidental second subscriptions.
        if legacy or effective_membership(self.db, user):
            raise HTTPException(409, "You already have a subscription. Contact support to change plans without duplicate billing.")
        previous = self.db.scalar(select(Intent).where(Intent.user_id == user.id,
            Intent.tenant_id == user.tenant_id, Intent.command_id == str(command)))
        if previous and previous.plan_code != plan.code:
            raise HTTPException(409, "Checkout command already belongs to another plan.")
        # Reuse any pending checkout for this account, including another tab.
        pending = self.db.scalar(select(Intent).where(Intent.user_id == user.id,
            Intent.tenant_id == user.tenant_id).order_by(Intent.created_at.desc()).limit(1))
        if not previous and pending:
            if pending.plan_code != plan.code:
                raise HTTPException(409, "A checkout for another plan is pending. Contact support before starting another subscription.")
            previous = pending
        if previous is None:
            previous = Intent(id=uuid4(), user_id=user.id, tenant_id=user.tenant_id,
                command_id=str(command), plan_code=plan.code, catalog_version=VERSION,
                amount_minor=plan.amount_minor)
            self.db.add(previous)
            self.db.commit()  # Must survive an unknown provider response.
            lock_user(self.db, user.id)
            # Another request may have finished this intent while commit released
            # the lock. Refresh the identity map before calling the provider.
            self.db.refresh(previous)
        if previous.checkout_url:
            return {"provider": "whop", "checkout_url": previous.checkout_url}
        hosted = self.provider.create_checkout(TenantContext(str(user.tenant_id), str(user.id)),
            contract(previous), binding_for(plan.code, settings))
        previous.configuration_id, previous.checkout_url = hosted.configuration_id, hosted.purchase_url
        self.db.commit()
        return {"provider": "whop", "checkout_url": hosted.purchase_url}

    def resolve_intent(self, resource: dict) -> Intent:
        metadata = object_value(resource.get("metadata"))
        try:
            intent_id = UUID(str(metadata.get("nsauto_intent_id")))
        except ValueError as exc:
            raise WhopError("unknown_checkout_intent") from exc
        row = self.db.get(Intent, intent_id)
        if row is None or not row.configuration_id:
            raise WhopError("unknown_checkout_intent")
        if metadata != self.provider._metadata(contract(row)):
            raise WhopError("checkout_metadata_mismatch")
        user = self.db.get(User, row.user_id)
        if user is None or not user.is_active or user.tenant_id != row.tenant_id:
            raise WhopError("checkout_principal_changed")
        return row

    def reconcile_payment(self, payment_id: str, now: datetime) -> bool:
        payment = self.provider.retrieve("payments", payment_id)
        row = self.resolve_intent(payment)
        lock_user(self.db, row.user_id)
        verified = self.provider.verify_paid_period(payment_id, contract(row), binding_for(row.plan_code, settings), now=now)
        proof = verified.charge
        member = self.db.get(Membership, proof.membership_id)
        receipt = self.db.get(Receipt, payment_id)
        if member and (member.intent_id != row.id or member.user_id != row.user_id or member.tenant_id != row.tenant_id):
            raise WhopError("membership_already_owned")
        if receipt and (receipt.intent_id != row.id or receipt.membership_id != proof.membership_id):
            raise WhopError("payment_already_owned")
        if member is None:
            # Negative evidence can never create an entitlement.
            if proof.revoked:
                return False
            member = Membership(membership_id=proof.membership_id, intent_id=row.id,
                user_id=row.user_id, tenant_id=row.tenant_id, customer_id=verified.customer_id,
                plan_code=row.plan_code, active=False, terminal=False, checked_at=now)
            self.db.add(member)
            self.db.flush()
        if receipt is None:
            receipt = Receipt(payment_id=payment_id, membership_id=proof.membership_id, intent_id=row.id, revoked=False)
            self.db.add(receipt)
        receipt.revoked = receipt.revoked or proof.revoked
        # Refunds/disputes are terminal; a delayed positive event cannot revive them.
        member.terminal = member.terminal or receipt.revoked
        if verified.ends_at and member.current_period_end and utc(verified.ends_at) < utc(member.current_period_end):
            if not member.terminal:
                return False
        member.active = not member.terminal and not proof.revoked
        member.checked_at = now
        if verified.ends_at:
            member.current_period_start, member.current_period_end = verified.starts_at, verified.ends_at
            member.cancel_at_period_end = verified.cancel_at_period_end
        self.project(member, row, payment_id)
        self.db.flush()
        return member.active

    def project(self, member: Membership, intent: Intent, payment_id: str) -> None:
        price = Decimal(intent.amount_minor) / 100
        local = self.db.scalar(select(Plan).where(Plan.name == LOCAL_NAMES[intent.plan_code],
            Plan.price == price, Plan.interval == PlanInterval.monthly))
        if local is None:
            raise WhopError("local_catalog_missing")
        provider_id = "whop:" + member.membership_id
        sub = self.db.scalar(select(Subscription).where(Subscription.stripe_subscription_id == provider_id))
        if sub is None:
            sub = Subscription(user_id=intent.user_id, tenant_id=intent.tenant_id,
                stripe_customer_id="whop:" + member.customer_id,
                stripe_subscription_id=provider_id, plan_id=local.id)
            self.db.add(sub)
        if sub.user_id != intent.user_id or sub.tenant_id != intent.tenant_id:
            raise WhopError("projection_owner_mismatch")
        sub.status = SubscriptionStatus.ACTIVE if member.active and not member.terminal else SubscriptionStatus.CANCELED
        sub.current_period_start, sub.current_period_end = member.current_period_start, member.current_period_end
        sub.cancel_at_period_end = member.cancel_at_period_end
        saved = self.db.scalar(select(Payment).where(Payment.provider_payment_id == "whop:" + payment_id))
        if saved is None:
            saved = Payment(user_id=intent.user_id, tenant_id=intent.tenant_id, plan_id=local.id,
                provider="whop", provider_payment_id="whop:" + payment_id,
                provider_order_id=member.membership_id, amount=price, currency="USD", status="captured")
            self.db.add(saved)
        if member.terminal:
            saved.status = "revoked"

    def refresh_membership(self, membership_id: str, now: datetime) -> None:
        resource = self.provider.retrieve("memberships", membership_id)
        row = self.resolve_intent(resource)
        binding = binding_for(row.plan_code, settings)
        if (object_value(resource.get("account")).get("id") != self.provider.settings.account_id
            or resource.get("product_id") != binding.product_id or resource.get("variant_id") != binding.variant_id):
            raise WhopError("membership_contract_mismatch")
        lock_user(self.db, row.user_id)
        member = self.db.get(Membership, membership_id)
        if member and (member.intent_id != row.id or member.user_id != row.user_id or member.tenant_id != row.tenant_id):
            raise WhopError("membership_already_owned")
        if resource.get("status") != "active":
            if member:
                member.active = False
                member.checked_at = now
                # Preserve receipt history, but make compatibility row inactive too.
                sub = self.db.scalar(select(Subscription).where(Subscription.stripe_subscription_id == "whop:" + membership_id))
                if sub:
                    sub.status = SubscriptionStatus.EXPIRED
            return
        starts = provider_timestamp(resource.get("current_period_start"))
        ids = self.provider.payment_candidates(membership_id, starts)
        for payment_id in ids:
            try:
                if self.reconcile_payment(payment_id, now):
                    return
            except WhopError as exc:
                if str(exc) not in {"payment_period_mismatch", "payment_contract_mismatch"}:
                    raise
        # No paid receipt for this period. Never carry a previous period forward.
        if member:
            member.active = False
            member.checked_at = now
