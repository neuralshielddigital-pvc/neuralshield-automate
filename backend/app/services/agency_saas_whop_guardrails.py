"""Fail-closed, provider-neutral guardrails for Whop recurring SaaS entitlements.

This module deliberately performs *no* webhook authentication, HTTP requests or
database writes. Call it ONLY with facts independently retrieved from Whop
after signature verification. It cannot grant access by itself. Existing Agency
Client Engine one-time purchases must continue through the separate adapter.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Mapping


class EntitlementState(str, Enum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    EXPIRED = "expired"
    REFUNDED = "refunded"


@dataclass(frozen=True)
class RecurringPlan:
    product_id: str
    checkout_plan_id: str
    tier: str
    monthly_usd_cents: int


@dataclass(frozen=True)
class VerifiedSubscriptionFacts:
    """Normalized, authoritative provider snapshot; never raw webhook JSON."""

    merchant_id: str
    product_id: str
    checkout_plan_id: str
    subscription_id: str
    customer_id: str
    provider_status: str
    amount_usd_cents: int
    currency: str
    billing_interval: str
    observed_at: datetime


@dataclass(frozen=True)
class SubscriptionDecision:
    subscription_id: str
    tier: str
    state: EntitlementState
    can_access: bool
    observed_at: datetime


SUPPORTED_STATUSES: Mapping[str, EntitlementState] = {
    "active": EntitlementState.ACTIVE,
    "trialing": EntitlementState.INACTIVE,  # trials must not grant paid access
    "past_due": EntitlementState.PAST_DUE,
    "unpaid": EntitlementState.PAST_DUE,
    "canceled": EntitlementState.CANCELED,
    "cancelled": EntitlementState.CANCELED,
    "expired": EntitlementState.EXPIRED,
    "refunded": EntitlementState.REFUNDED,
    "incomplete": EntitlementState.INACTIVE,
}


def validate_recurring_snapshot(
    *,
    snapshot: VerifiedSubscriptionFacts,
    independently_verified: bool,
    expected_merchant_id: str,
    allowed_plans: Mapping[str, RecurringPlan],
    bound_customer_id: str,
    previous: SubscriptionDecision | None = None,
) -> SubscriptionDecision:
    """Decide whether authoritative recurring facts permit paid SaaS access.

    The *caller* must independently authenticate the event, fetch current
    subscription/payment facts using a server credential, link provider
    customer ID to an already authenticated tenant owner, and persist decisions
    transactionally with a unique subscription identity. In particular:
    a checkout email must never be sufficient to bind an account.
    """
    if not independently_verified:
        raise ValueError("Provider snapshot was not independently verified")
    if not expected_merchant_id.startswith("biz_") or snapshot.merchant_id != expected_merchant_id:
        raise ValueError("Wrong or unconfigured Whop merchant")
    if not snapshot.subscription_id.strip() or not snapshot.customer_id.strip():
        raise ValueError("Missing provider subscription/customer identity")
    if not bound_customer_id.strip() or snapshot.customer_id != bound_customer_id:
        raise ValueError("Provider customer does not match bound tenant identity")
    plan = allowed_plans.get(snapshot.checkout_plan_id)
    if plan is None or plan.checkout_plan_id != snapshot.checkout_plan_id:
        raise ValueError("Unknown or unapproved Whop subscription plan")
    if plan.product_id != snapshot.product_id:
        raise ValueError("Checkout plan and product mismatch")
    if plan.monthly_usd_cents <= 0 or not plan.tier.strip():
        raise ValueError("Invalid configured plan")
    if snapshot.currency.upper() != "USD" or snapshot.billing_interval.lower() not in {"month", "monthly", "1 month"}:
        raise ValueError("Unexpected subscription currency or period")
    if snapshot.amount_usd_cents != plan.monthly_usd_cents:
        raise ValueError("Unexpected subscription price")
    if snapshot.observed_at.tzinfo is None or snapshot.observed_at.utcoffset() is None:
        raise ValueError("Snapshot timestamp must be timezone-aware")
    if snapshot.observed_at > datetime.now(timezone.utc):
        raise ValueError("Future provider snapshot")
    state = SUPPORTED_STATUSES.get(snapshot.provider_status.lower())
    if state is None:
        raise ValueError("Unrecognized provider subscription status")
    if previous is not None:
        if previous.subscription_id != snapshot.subscription_id:
            raise ValueError("Subscription identity cannot change")
        if snapshot.observed_at < previous.observed_at:
            raise ValueError("Stale provider snapshot")
        if snapshot.observed_at == previous.observed_at and state != previous.state:
            raise ValueError("Conflicting same-time provider snapshot")
        # Require a fresh verified provider snapshot before restoring access
        # after terminal statuses; never reactivate from delayed payment events.
        if previous.state in {EntitlementState.CANCELED, EntitlementState.EXPIRED, EntitlementState.REFUNDED} and state == EntitlementState.ACTIVE:
            raise ValueError("Terminal subscription cannot be silently reactivated")
    return SubscriptionDecision(
        subscription_id=snapshot.subscription_id,
        tier=plan.tier,
        state=state,
        can_access=state == EntitlementState.ACTIVE,
        observed_at=snapshot.observed_at,
    )
