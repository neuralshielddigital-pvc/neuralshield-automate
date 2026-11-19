"""Payment-backed recurring decision gate; no provider I/O or database writes.

Use only with independently authenticated provider subscription AND payment
records. The ordinary subscription validator is not sufficient to grant paid
access. This module is staging-only until the provider adapter is verified.
"""
from __future__ import annotations

from typing import Mapping

from app.services.agency_saas_whop_first_charge import (
    VerifiedFirstCharge,
    validate_first_charge,
)
from app.services.agency_saas_whop_guardrails import (
    RecurringPlan,
    SubscriptionDecision,
    VerifiedSubscriptionFacts,
    validate_recurring_snapshot,
)


def validate_paid_recurring_snapshot(
    *,
    snapshot: VerifiedSubscriptionFacts,
    charge: VerifiedFirstCharge,
    subscription_independently_verified: bool,
    charge_independently_verified: bool,
    expected_merchant_id: str,
    allowed_plans: Mapping[str, RecurringPlan],
    bound_customer_id: str,
    previous: SubscriptionDecision | None = None,
) -> SubscriptionDecision:
    """Reject active access unless the first payment independently verifies.

    Non-active snapshots are still validated and may revoke access without a
    payment lookup, so refunds/cancellations never depend on payment API uptime.
    """
    decision = validate_recurring_snapshot(
        snapshot=snapshot,
        independently_verified=subscription_independently_verified,
        expected_merchant_id=expected_merchant_id,
        allowed_plans=allowed_plans,
        bound_customer_id=bound_customer_id,
        previous=previous,
    )
    if decision.can_access:
        validate_first_charge(
            charge=charge,
            independently_verified=charge_independently_verified,
            subscription_id=snapshot.subscription_id,
            customer_id=bound_customer_id,
            merchant_id=expected_merchant_id,
            expected_amount_usd_cents=snapshot.amount_usd_cents,
        )
    return decision
