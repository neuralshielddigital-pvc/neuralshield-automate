"""Transactional, default-deny persistence for pre-bound Whop SaaS identities.

An authenticated account-claim flow must create each binding separately.
This implementation does NOT create users, subscriptions, entitlements, or
bindings from webhooks and does not change legacy Paddle billing records.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
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
