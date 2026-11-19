from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from app.services.agency_saas_whop_first_charge import VerifiedFirstCharge
from app.services.agency_saas_whop_guardrails import RecurringPlan, VerifiedSubscriptionFacts
from app.services.agency_saas_whop_paid_decision import validate_paid_recurring_snapshot


NOW = datetime.now(timezone.utc) - timedelta(minutes=5)
PLAN = RecurringPlan("prod_i6Ll01S4m3jmI", "plan_Ne9TiMmqGDAIC", "starter", 1900)
SNAPSHOT = VerifiedSubscriptionFacts(
    merchant_id="biz_testmerchant", product_id=PLAN.product_id,
    checkout_plan_id=PLAN.checkout_plan_id, subscription_id="sub_123",
    customer_id="cus_123", provider_status="active", amount_usd_cents=1900,
    currency="USD", billing_interval="month", observed_at=NOW,
)
CHARGE = VerifiedFirstCharge(
    payment_id="pay_123", subscription_id="sub_123",
    customer_id="cus_123", merchant_id="biz_testmerchant",
    status="paid", amount_usd_cents=1900, currency="USD", paid_at=NOW,
)


def decide(snapshot=SNAPSHOT, charge=CHARGE, verified=True):
    return validate_paid_recurring_snapshot(
        snapshot=snapshot, charge=charge,
        subscription_independently_verified=True,
        charge_independently_verified=verified,
        expected_merchant_id="biz_testmerchant",
        allowed_plans={PLAN.checkout_plan_id: PLAN},
        bound_customer_id="cus_123",
    )


def test_paid_matching_first_charge_allows_access():
    assert decide().can_access is True


@pytest.mark.parametrize("charge", [
    replace(CHARGE, status="failed"),
    replace(CHARGE, status="refunded"),
    replace(CHARGE, subscription_id="sub_other"),
    replace(CHARGE, customer_id="cus_other"),
    replace(CHARGE, merchant_id="biz_other"),
    replace(CHARGE, amount_usd_cents=5900),
    replace(CHARGE, currency="EUR"),
    replace(CHARGE, paid_at=NOW + timedelta(days=2)),
])
def test_bad_first_charge_never_grants_access(charge):
    with pytest.raises(ValueError):
        decide(charge=charge)


def test_unverified_charge_never_grants_access():
    with pytest.raises(ValueError):
        decide(verified=False)


@pytest.mark.parametrize("status", ["canceled", "refunded", "past_due", "expired"])
def test_revocation_does_not_require_payment_api(status):
    result = decide(snapshot=replace(SNAPSHOT, provider_status=status),
                    charge=None, verified=False)
    assert result.can_access is False


def test_unverified_subscription_fails_even_with_paid_charge():
    with pytest.raises(ValueError):
        validate_paid_recurring_snapshot(
            snapshot=SNAPSHOT, charge=CHARGE,
            subscription_independently_verified=False,
            charge_independently_verified=True,
            expected_merchant_id="biz_testmerchant",
            allowed_plans={PLAN.checkout_plan_id: PLAN},
            bound_customer_id="cus_123",
        )
