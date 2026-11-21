from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from app.services.agency_saas_whop_first_charge import VerifiedFirstCharge
from app.services.agency_saas_whop_period_payment import (
    VerifiedPeriodPayment,
    validate_period_payment,
)

START = datetime(2026, 11, 1, tzinfo=timezone.utc)
END = datetime(2026, 12, 1, tzinfo=timezone.utc)
CHARGE = VerifiedFirstCharge(
    payment_id="pay_1", subscription_id="sub_1", customer_id="cus_1",
    merchant_id="biz_1", status="paid", amount_usd_cents=1900,
    currency="USD", paid_at=START + timedelta(hours=1),
)
EVIDENCE = VerifiedPeriodPayment(CHARGE, START, END)


def check(evidence=EVIDENCE, start=START, end=END, verified=True):
    validate_period_payment(
        evidence=evidence, independently_verified=verified,
        subscription_id="sub_1", customer_id="cus_1", merchant_id="biz_1",
        expected_amount_usd_cents=1900, entitlement_start=start,
        entitlement_end=end,
    )


def test_matching_authenticated_period_is_accepted():
    check()


@pytest.mark.parametrize("start,end", [
    (END, END + timedelta(days=30)),
    (START - timedelta(seconds=1), END),
    (START, END + timedelta(seconds=1)),
    (END, END),
])
def test_uncovered_or_invalid_entitlement_is_rejected(start, end):
    with pytest.raises(ValueError):
        check(start=start, end=end)


@pytest.mark.parametrize("evidence", [
    None,
    VerifiedPeriodPayment(CHARGE, END, START),
    VerifiedPeriodPayment(CHARGE, START.replace(tzinfo=None), END),
    VerifiedPeriodPayment(replace(CHARGE, status="refunded"), START, END),
    VerifiedPeriodPayment(replace(CHARGE, customer_id="other"), START, END),
    VerifiedPeriodPayment(replace(CHARGE, paid_at=END + timedelta(seconds=1)), START, END),
    VerifiedPeriodPayment(replace(CHARGE, paid_at=START - timedelta(seconds=1)), START, END),
])
def test_invalid_or_unbound_period_evidence_is_rejected(evidence):
    with pytest.raises(ValueError):
        check(evidence=evidence)


def test_unverified_provider_evidence_is_rejected():
    with pytest.raises(ValueError):
        check(verified=False)


def test_first_charge_cannot_unlock_next_month():
    with pytest.raises(ValueError):
        check(start=END, end=END + timedelta(days=31))
