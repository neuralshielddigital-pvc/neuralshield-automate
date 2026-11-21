"""Fail-closed first-charge evidence gate for Agency Whop recurring billing.

Only construct these facts from an authenticated, independently fetched payment
record. A webhook payload or membership 'active' status is not payment evidence.
This module does not infer Whop's API response schema or grant access.
"""
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class VerifiedFirstCharge:
    payment_id: str
    subscription_id: str
    customer_id: str
    merchant_id: str
    status: str
    amount_usd_cents: int
    currency: str
    paid_at: datetime


def validate_first_charge(
    *,
    charge: VerifiedFirstCharge,
    independently_verified: bool,
    subscription_id: str,
    customer_id: str,
    merchant_id: str,
    expected_amount_usd_cents: int,
) -> None:
    """Raise unless the independently retrieved first charge is paid and bound.

    Must be combined with current subscription validation and persisted tenant
    ownership; it is not by itself sufficient to activate an entitlement.
    """
    if independently_verified is not True:
        raise ValueError("First charge not independently verified")
    if not isinstance(charge, VerifiedFirstCharge):
        raise ValueError("Invalid first charge evidence")
    if any(not isinstance(value, str) for value in (
        charge.payment_id, charge.subscription_id, charge.customer_id,
        charge.merchant_id, charge.status, charge.currency,
        subscription_id, customer_id, merchant_id,
    )):
        raise ValueError("Invalid first charge identity fields")
    if not charge.payment_id.strip() or not charge.subscription_id.strip():
        raise ValueError("Missing payment or subscription identity")
    if not charge.customer_id.strip() or not charge.merchant_id.strip():
        raise ValueError("Missing customer or merchant identity")
    if not subscription_id.strip() or charge.subscription_id != subscription_id:
        raise ValueError("Payment subscription mismatch")
    if not customer_id.strip() or charge.customer_id != customer_id:
        raise ValueError("Payment customer mismatch")
    if not merchant_id.strip() or charge.merchant_id != merchant_id:
        raise ValueError("Payment merchant mismatch")
    if charge.status.lower() not in {"paid", "succeeded"}:
        raise ValueError("First charge has not succeeded")
    if (not isinstance(expected_amount_usd_cents, int) or isinstance(expected_amount_usd_cents, bool)
            or not isinstance(charge.amount_usd_cents, int) or isinstance(charge.amount_usd_cents, bool)
            or expected_amount_usd_cents <= 0 or charge.amount_usd_cents != expected_amount_usd_cents):
        raise ValueError("First charge amount mismatch")
    if charge.currency.upper() != "USD":
        raise ValueError("First charge currency mismatch")
    if not isinstance(charge.paid_at, datetime) or charge.paid_at.tzinfo is None or charge.paid_at.utcoffset() is None:
        raise ValueError("First charge timestamp must be timezone-aware")
    if charge.paid_at > datetime.now(timezone.utc):
        raise ValueError("Future first charge timestamp")
