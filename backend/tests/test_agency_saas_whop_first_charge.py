"""Synthetic first-charge gate tests; no external requests or charges."""
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from app.services.agency_saas_whop_first_charge import VerifiedFirstCharge, validate_first_charge


BASE = VerifiedFirstCharge(
    payment_id="pay_synthetic", subscription_id="sub_synthetic",
    customer_id="cus_synthetic", merchant_id="biz_synthetic",
    status="paid", amount_usd_cents=1900, currency="USD",
    paid_at=datetime(2026, 11, 15, tzinfo=timezone.utc),
)


def check(charge=BASE, verified=True):
    validate_first_charge(
        charge=charge, independently_verified=verified,
        subscription_id="sub_synthetic", customer_id="cus_synthetic",
        merchant_id="biz_synthetic", expected_amount_usd_cents=1900,
    )


def test_verified_paid_first_charge_passes():
    check()


@pytest.mark.parametrize("patch", [
    {"payment_id": ""}, {"subscription_id": "sub_other"},
    {"customer_id": "cus_other"}, {"merchant_id": "biz_other"},
    {"status": "pending"}, {"status": "refunded"}, {"status": "failed"},
    {"amount_usd_cents": 0}, {"amount_usd_cents": 5900},
    {"currency": "EUR"}, {"paid_at": datetime(2026, 11, 15)},
    {"paid_at": datetime(2099, 1, 1, tzinfo=timezone.utc)},
])
def test_bad_payment_evidence_fails_closed(patch):
    with pytest.raises(ValueError):
        check(replace(BASE, **patch))


def test_unverified_webhook_cannot_supply_payment_evidence():
    with pytest.raises(ValueError, match="independently verified"):
        check(verified=False)
