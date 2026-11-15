"""Synthetic tests: no payment, external network, or database access."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from app.services.agency_saas_whop_guardrails import (
    EntitlementState,
    RecurringPlan,
    VerifiedSubscriptionFacts,
    validate_recurring_snapshot,
)

MERCHANT = "biz_test_agency_only"
CUSTOMER = "cus_synthetic_bound_123"
WHEN = datetime(2026, 11, 15, tzinfo=timezone.utc)
PLANS = {
    "plan_starter": RecurringPlan(
        product_id="prod_starter", checkout_plan_id="plan_starter",
        tier="starter", monthly_usd_cents=1900,
    ),
    "plan_pro": RecurringPlan(
        product_id="prod_pro", checkout_plan_id="plan_pro",
        tier="pro", monthly_usd_cents=5900,
    ),
    "plan_business": RecurringPlan(
        product_id="prod_business", checkout_plan_id="plan_business",
        tier="business", monthly_usd_cents=14900,
    ),
}


def facts(plan="plan_starter", status="active"):
    selected = PLANS[plan]
    return VerifiedSubscriptionFacts(
        merchant_id=MERCHANT, product_id=selected.product_id,
        checkout_plan_id=plan, subscription_id="sub_synthetic",
        customer_id=CUSTOMER, provider_status=status,
        amount_usd_cents=selected.monthly_usd_cents,
        currency="USD", billing_interval="month", observed_at=WHEN,
    )


def decide(snapshot=None, **kwargs):
    args = dict(
        snapshot=snapshot or facts(), independently_verified=True,
        expected_merchant_id=MERCHANT, allowed_plans=PLANS,
        bound_customer_id=CUSTOMER,
    )
    args.update(kwargs)
    return validate_recurring_snapshot(**args)


@pytest.mark.parametrize("plan,tier", [
    ("plan_starter", "starter"), ("plan_pro", "pro"), ("plan_business", "business")
])
def test_all_monthly_plans_allow_verified_active_access(plan, tier):
    result = decide(facts(plan))
    assert result.tier == tier
    assert result.state == EntitlementState.ACTIVE
    assert result.can_access is True


@pytest.mark.parametrize("status", [
    "past_due", "unpaid", "canceled", "expired", "refunded", "incomplete", "trialing"
])
def test_non_active_states_do_not_grant(status):
    assert not decide(facts(status=status)).can_access


@pytest.mark.parametrize("patch", [
    {"merchant_id": "biz_wrong"},
    {"customer_id": "cus_other"},
    {"product_id": "prod_one_time_agency_toolkit"},
    {"checkout_plan_id": "plan_one_time"},
    {"amount_usd_cents": 2700},
    {"currency": "EUR"},
    {"billing_interval": "year"},
    {"provider_status": "unknown"},
    {"subscription_id": ""},
    {"observed_at": datetime(2026, 11, 15)},
    {"observed_at": datetime(2099, 1, 1, tzinfo=timezone.utc)},
])
def test_invalid_provider_facts_fail_closed(patch):
    with pytest.raises(ValueError):
        decide(replace(facts(), **patch))


def test_unverified_payload_cannot_grant():
    with pytest.raises(ValueError, match="independently verified"):
        decide(independently_verified=False)


def test_email_or_unbound_customer_cannot_claim_tenant():
    with pytest.raises(ValueError, match="bound tenant"):
        decide(bound_customer_id="email@example.com")


def test_stale_renewal_cannot_override_revocation():
    revoked = decide(facts(status="refunded"))
    with pytest.raises(ValueError, match="Terminal"):
        decide(replace(facts(), observed_at=WHEN + timedelta(hours=1)), previous=revoked)


def test_out_of_order_event_rejected():
    old = decide(replace(facts(), observed_at=WHEN + timedelta(hours=1)))
    with pytest.raises(ValueError, match="Stale"):
        decide(facts(status="past_due"), previous=old)


def test_replay_same_state_is_safe():
    old = decide()
    assert decide(previous=old) == old


def test_conflicting_same_timestamp_rejected():
    old = decide()
    with pytest.raises(ValueError, match="Conflicting"):
        decide(facts(status="canceled"), previous=old)


def test_newer_cancellation_revokes_access():
    old = decide()
    change = replace(facts(status="canceled"), observed_at=WHEN + timedelta(hours=1))
    result = decide(change, previous=old)
    assert result.state == EntitlementState.CANCELED
    assert result.can_access is False


def test_other_subscription_identity_cannot_reuse_state():
    old = decide()
    with pytest.raises(ValueError, match="identity"):
        decide(replace(facts(), subscription_id="sub_other"), previous=old)


def test_empty_or_duplicate_unsafe_configuration():
    with pytest.raises(ValueError):
        decide(allowed_plans={"plan_starter": replace(PLANS["plan_starter"], monthly_usd_cents=0)})
