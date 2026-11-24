from datetime import datetime, timezone

UTC = timezone.utc

import pytest
from test_automation_whop_transport import adapter, binding, intent, resources

from app.services.automation_whop_transport import WhopError, provider_timestamp

NOW = datetime(2026, 11, 15, 12, tzinfo=UTC)


def period_resources() -> dict[str, dict[str, object]]:
    data = resources()
    data["/api/v1/payments/pay_test"]["paid_at"] = "2026-11-15T11:59:00Z"
    data["/api/v1/memberships/mem_test"].update(
        current_period_start="2026-11-14T12:00:00Z",
        current_period_end="2026-12-14T12:00:00Z",
        billing_period_days=30,
        cancel_at_period_end=True,
        user_id="user_test",
    )
    return data


def test_paid_receipt_confirms_only_its_current_period_even_if_canceling() -> None:
    proof = adapter(period_resources(), []).verify_paid_period(
        "pay_test", intent(), binding(), now=NOW
    )
    assert not proof.charge.revoked
    assert proof.starts_at == datetime(2026, 11, 14, 12, tzinfo=UTC)
    assert proof.ends_at == datetime(2026, 12, 14, 12, tzinfo=UTC)
    assert proof.checked_at == NOW


@pytest.mark.parametrize(
    "key,value",
    [
        ("current_period_start", None),
        ("current_period_end", "2026-11-15T12:00:00Z"),
        ("current_period_start", "2026-11-16T12:00:00Z"),
        ("current_period_end", "2027-12-14T12:00:00Z"),
        ("billing_period_days", True),
        ("billing_period_days", 365),
    ],
)
def test_invalid_or_expired_period_does_not_produce_positive_evidence(
    key: str, value: object
) -> None:
    data = period_resources()
    data["/api/v1/memberships/mem_test"][key] = value
    with pytest.raises(WhopError):
        adapter(data, []).verify_paid_period("pay_test", intent(), binding(), now=NOW)


@pytest.mark.parametrize(
    "paid", ["2026-10-15T12:00:00Z", "2026-12-15T12:00:00Z", "2026-11-15T12:10:00Z"]
)
def test_old_or_future_payment_cannot_activate_a_new_renewal_period(paid: str) -> None:
    data = period_resources()
    data["/api/v1/payments/pay_test"]["paid_at"] = paid
    with pytest.raises(WhopError, match="payment_period_mismatch"):
        adapter(data, []).verify_paid_period("pay_test", intent(), binding(), now=NOW)


def test_refund_or_inactive_membership_produces_revocation_only_without_dates() -> None:
    data = resources()
    data["/api/v1/payments/pay_test"]["refunded_amount"] = {"currency": "usd", "amount": "1.00"}
    proof = adapter(data, []).verify_paid_period("pay_test", intent(), binding(), now=NOW)
    assert proof.charge.revoked and proof.starts_at is None and proof.ends_at is None


@pytest.mark.parametrize(
    "value", [None, 123, "2026-11-15", "2026-11-15T12:00:00", "not-a-timestamp"]
)
def test_provider_period_dates_require_bounded_aware_iso_timestamps(value: object) -> None:
    with pytest.raises(WhopError):
        provider_timestamp(value)
