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


@pytest.mark.parametrize("patch", [
    {"payment_id": None}, {"subscription_id": 42},
    {"customer_id": None}, {"merchant_id": []},
    {"status": None}, {"currency": None},
    {"amount_usd_cents": True}, {"amount_usd_cents": "1900"},
    {"paid_at": None}, {"paid_at": "2026-11-15"},
])
def test_malformed_provider_evidence_fails_closed(patch):
    with pytest.raises(ValueError):
        check(replace(BASE, **patch))


@pytest.mark.parametrize("expected", [True, "1900", 0, None])
def test_malformed_expected_amount_fails_closed(expected):
    with pytest.raises(ValueError):
        validate_first_charge(
            charge=BASE, independently_verified=True,
            subscription_id="sub_synthetic", customer_id="cus_synthetic",
            merchant_id="biz_synthetic", expected_amount_usd_cents=expected,
        )


def test_malformed_verified_flag_fails_closed():
    with pytest.raises(ValueError):
        check(verified=1)
