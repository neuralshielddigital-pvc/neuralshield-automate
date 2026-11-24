"""Transactional, default-deny persistence for pre-bound Whop SaaS identities.

An authenticated account-claim flow must create each binding separately.
This implementation does NOT create users, subscriptions, entitlements, or
bindings from webhooks and does not change legacy Paddle billing records.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.whop_saas_subscription import WhopSaasSubscriptionBinding
from app.services.agency_saas_whop_guardrails import (
    EntitlementState, SubscriptionDecision,
)
from app.services.agency_saas_whop_lifecycle import AccountBinding


def aware(value: datetime) -> datetime:
    """Normalize driver-returned UTC; PostgreSQL retains the timezone."""
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class SQLAlchemyWhopSaasBindingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _row(self, subscription_id: str, *, lock: bool = False):
        statement = select(WhopSaasSubscriptionBinding).where(
            WhopSaasSubscriptionBinding.provider_subscription_id == subscription_id
        )
        if lock:
            statement = statement.with_for_update()
        return self.db.scalar(statement)

    def create_binding_if_absent(self, binding: AccountBinding) -> bool:
        """Insert a disabled binding; reject claims by a different user.

        A unique provider_subscription_id index serializes first claim across
        workers. On unique collision, check the committed owner. No subscription
        tier or paid access is written by this method.
        """
        if (
            not binding.subscription_id.strip()
            or not binding.provider_customer_id.strip()
            or not binding.user_id.strip()
            or not binding.tenant_id.strip()
        ):
            raise ValueError("Incomplete verified account binding")
        try:
            tenant_id = UUID(binding.tenant_id)
            user_id = UUID(binding.user_id)
        except ValueError as exc:
            raise ValueError("Invalid authenticated tenant or user identity") from exc
        existing = self._row(binding.subscription_id)
        if existing is not None:
            if (
                existing.provider_customer_id == binding.provider_customer_id
                and existing.tenant_id == tenant_id
                and existing.user_id == user_id
            ):
                # The initial SELECT starts a transaction. An idempotent claim
                # must not leave it open across later request processing.
                self.db.rollback()
                return False
            self.db.rollback()
            raise ValueError("Subscription already belongs to a different SaaS account")
        try:
            self.db.add(WhopSaasSubscriptionBinding(
                provider_subscription_id=binding.subscription_id,
                provider_customer_id=binding.provider_customer_id,
                tenant_id=tenant_id, user_id=user_id,
                tier="unverified", access_state="inactive", access_enabled=False,
                provider_observed_at=None,
            ))
            self.db.commit()
            return True
        except IntegrityError:
            self.db.rollback()
            # A concurrent insert may have won the unique subscription key.
            # Fail closed if any unrelated FK/constraint error occurred.
            existing = self._row(binding.subscription_id)
            if existing is None:
                raise
            if (
                existing.provider_customer_id == binding.provider_customer_id
                and existing.tenant_id == tenant_id
                and existing.user_id == user_id
            ):
                # The collision follow-up SELECT opens a new transaction.
                # Release it before returning an idempotent claim result.
                self.db.rollback()
                return False
            self.db.rollback()
            raise ValueError("Subscription already belongs to a different SaaS account")
        except Exception:
            self.db.rollback()
            raise

    def create_binding_in_transaction(self, binding: AccountBinding) -> bool:
        """Insert a disabled binding without committing the caller's nonce transaction.

        IntegrityError must propagate so the caller rolls back both the nonce
        redemption and binding insert. Never rollback here: that would break
        atomicity with the authorization service.
        """
        if not all(
            isinstance(value, str) and value.strip()
            for value in (
                binding.subscription_id, binding.provider_customer_id,
                binding.tenant_id, binding.user_id,
            )
        ):
            raise ValueError("Incomplete verified account binding")
        tenant_id = UUID(binding.tenant_id)
        user_id = UUID(binding.user_id)
        existing = self._row(binding.subscription_id, lock=True)
        if existing is not None:
            if (
                existing.provider_customer_id == binding.provider_customer_id
                and existing.tenant_id == tenant_id
                and existing.user_id == user_id
            ):
                return False
            raise ValueError("Subscription already belongs to a different SaaS account")
        self.db.add(WhopSaasSubscriptionBinding(
            provider_subscription_id=binding.subscription_id,
            provider_customer_id=binding.provider_customer_id,
            tenant_id=tenant_id, user_id=user_id,
            tier="unverified", access_state="inactive", access_enabled=False,
            provider_observed_at=None,
        ))
        self.db.flush()
        return True

    def list_due_subscription_ids(self, *, before: datetime, limit: int) -> list[str]:
        """Select only pre-existing identities due for provider reconciliation.

        Stable ordering and bounded result size prevent an unbounded sweep.
        No external requests or grants happen in this method.
        """
        from sqlalchemy import or_
        if type(limit) is not int or limit < 1 or limit > 100:
            raise ValueError("Reconciliation candidate limit must be 1..100")
        if before.tzinfo is None or before.utcoffset() is None:
            raise ValueError("Cutoff must have a timezone")
        statement = (
            select(WhopSaasSubscriptionBinding.provider_subscription_id)
            .where(or_(
                WhopSaasSubscriptionBinding.provider_observed_at.is_(None),
                WhopSaasSubscriptionBinding.provider_observed_at <= aware(before),
            ))
            .order_by(
                WhopSaasSubscriptionBinding.provider_observed_at.asc().nullsfirst(),
                WhopSaasSubscriptionBinding.provider_subscription_id.asc(),
            )
            .limit(limit)
        )
        return list(self.db.scalars(statement).all())

    def get_binding(self, subscription_id: str) -> AccountBinding | None:
        row = self._row(subscription_id)
        if row is None:
            return None
        return AccountBinding(
            subscription_id=row.provider_subscription_id,
            provider_customer_id=row.provider_customer_id,
            tenant_id=str(row.tenant_id),
            user_id=str(row.user_id),
        )

    def get_decision(self, subscription_id: str) -> SubscriptionDecision | None:
        row = self._row(subscription_id)
        if row is None or row.provider_observed_at is None:
            return None
        return SubscriptionDecision(
            subscription_id=row.provider_subscription_id,
            tier=row.tier,
            state=EntitlementState(row.access_state),
            can_access=row.access_enabled,
            observed_at=aware(row.provider_observed_at),
        )

    def apply_if_current(
        self, binding: AccountBinding, decision: SubscriptionDecision,
    ) -> bool:
        if decision.subscription_id != binding.subscription_id:
            raise ValueError("Subscription identity mismatch")
        try:
            # Row lock prevents concurrent webhooks from overwriting a newer
            # authoritative subscription snapshot.
            row = self._row(binding.subscription_id, lock=True)
            if row is None:
                raise ValueError("No authorized customer-to-tenant binding")
            if (
                row.provider_customer_id != binding.provider_customer_id
                or str(row.tenant_id) != binding.tenant_id
                or str(row.user_id) != binding.user_id
            ):
                raise ValueError("Existing tenant binding changed")
            if decision.can_access != (decision.state is EntitlementState.ACTIVE):
                raise ValueError("Inconsistent entitlement decision")
            if decision.observed_at.tzinfo is None:
                raise ValueError("Unaware provider timestamp")
            if row.provider_observed_at is not None:
                previous = aware(row.provider_observed_at)
                incoming = aware(decision.observed_at)
                if incoming < previous:
                    raise ValueError("Stale provider snapshot")
                if incoming == previous:
                    if (
                        row.tier == decision.tier
                        and row.access_state == decision.state.value
                        and row.access_enabled == decision.can_access
                    ):
                        # Release the SELECT FOR UPDATE lock on an idempotent
                        # replay; otherwise the caller's session can retain a
                        # PostgreSQL row lock until an unrelated request ends.
                        self.db.rollback()
                        return False
                    raise ValueError("Conflicting same-time provider snapshot")
                if (
                    row.access_state in {"canceled", "expired", "refunded"}
                    and decision.can_access
                ):
                    raise ValueError("Terminal subscription cannot silently reactivate")
            row.tier = decision.tier
            row.access_state = decision.state.value
            row.access_enabled = decision.can_access
            row.provider_observed_at = aware(decision.observed_at)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise
