"""Provider-agnostic, fail-closed renewal-period payment evidence gate.

Call only after independently authenticating the payment and subscription with
Whop. This validator is not a Whop API response parser and performs no I/O.
A first charge must never be reused to authorize a later billing period.
"""
from dataclasses import dataclass
from datetime import datetime, timezone

from app.services.agency_saas_whop_first_charge import (
    VerifiedFirstCharge,
    validate_first_charge,
)


@dataclass(frozen=True)
class VerifiedPeriodPayment:
    charge: VerifiedFirstCharge
    period_start: datetime
    period_end: datetime


def validate_period_payment(
    *,
    evidence: VerifiedPeriodPayment,
    independently_verified: bool,
    subscription_id: str,
    customer_id: str,
    merchant_id: str,
    expected_amount_usd_cents: int,
    entitlement_start: datetime,
    entitlement_end: datetime,
) -> None:
    """Require a successful, independently verified payment for this period.

    Period boundaries must come from an authenticated provider record, not
    checkout query parameters or webhook payloads. The covered interval must
    contain the requested entitlement interval, and payment must occur no
    later than the period end. Does not activate entitlements by itself.
    """
    if not isinstance(evidence, VerifiedPeriodPayment):
        raise ValueError("Missing authenticated period payment evidence")
    validate_first_charge(
        charge=evidence.charge,
        independently_verified=independently_verified,
        subscription_id=subscription_id,
        customer_id=customer_id,
        merchant_id=merchant_id,
        expected_amount_usd_cents=expected_amount_usd_cents,
    )
    dates = (evidence.period_start, evidence.period_end,
             entitlement_start, entitlement_end)
    if any(not isinstance(d, datetime) or d.tzinfo is None
           or d.utcoffset() is None for d in dates):
        raise ValueError("Billing period timestamps must be timezone-aware")
    period_start, period_end, requested_start, requested_end = (
        d.astimezone(timezone.utc) for d in dates
    )
    if not (period_start < period_end and requested_start < requested_end):
        raise ValueError("Invalid billing period")
    if not (period_start <= requested_start and requested_end <= period_end):
        raise ValueError("Payment does not cover requested entitlement period")
    if evidence.charge.paid_at.astimezone(timezone.utc) > period_end:
        raise ValueError("Payment occurred after covered period")
