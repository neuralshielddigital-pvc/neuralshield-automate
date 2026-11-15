"""Synthetic lifecycle tests: independent provider state, no live payments."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from app.services.agency_saas_whop_guardrails import (
    EntitlementState, RecurringPlan, VerifiedSubscriptionFacts,
)
from app.services.agency_saas_whop_lifecycle import (
    AccountBinding, AuthenticatedWebhookReference, ProcessingResult,
    process_verified_subscription_event,
)

NOW = datetime(2026, 11, 15, tzinfo=timezone.utc)
PLAN = RecurringPlan("prod_starter", "plan_starter", "starter", 1900)


def snapshot(status="active", **overrides):
    data = dict(
        merchant_id="biz_test", product_id="prod_starter",
        checkout_plan_id="plan_starter", subscription_id="sub_test",
        customer_id="cus_bound", provider_status=status,
        amount_usd_cents=1900, currency="USD", billing_interval="month",
        observed_at=NOW,
    )
    data.update(overrides)
    return VerifiedSubscriptionFacts(**data)


class FakeProvider:
    def __init__(self, current):
        self.current = current
        self.lookups = 0

    def retrieve_verified_subscription(self, subscription_id):
        self.lookups += 1
        return self.current


class FakeRepo:
    def __init__(self, binding=None):
        self.binding = binding or AccountBinding(
            "sub_test", "cus_bound", "tenant_1", "user_1"
        )
        self.previous = None
        self.writes = []

    def get_binding(self, subscription_id):
        return self.binding

    def get_decision(self, subscription_id):
        return self.previous

    def apply_if_current(self, binding, decision):
        # A stand-in for required durable compare-and-swap behavior.
        if self.previous == decision:
            return False
        self.previous = decision
        self.writes.append((binding, decision))
        return True


def event(event_type="membership.went_valid", subscription_id="sub_test"):
    return AuthenticatedWebhookReference("evt_test", event_type, subscription_id)


def run(provider=None, repo=None, evt=None, **kw):
    args = dict(
        event=evt or event(), signature_verified=True,
        provider=provider or FakeProvider(snapshot()),
        repository=repo or FakeRepo(),
        expected_merchant_id="biz_test",
        allowed_plans={"plan_starter": PLAN},
    )
    args.update(kw)
    return process_verified_subscription_event(**args)


def test_fresh_active_provider_grants_bound_tenant_only():
    repo = FakeRepo()
    provider = FakeProvider(snapshot())
    result = run(provider=provider, repo=repo)
    assert isinstance(result, ProcessingResult)
    assert result.handled and result.changed and result.decision.can_access
    assert provider.lookups == 1
    assert repo.writes[0][0].tenant_id == "tenant_1"


def test_duplicate_delivery_is_noop():
    repo = FakeRepo()
    run(repo=repo)
    result = run(repo=repo)
    assert result.handled and not result.changed
    assert len(repo.writes) == 1


def test_cancellation_revokes_bound_access():
    repo = FakeRepo()
    provider = FakeProvider(snapshot())
    run(repo=repo, provider=provider)
    provider.current = snapshot("canceled", observed_at=NOW + timedelta(minutes=5))
    result = run(repo=repo, provider=provider, evt=event("membership.went_invalid"))
    assert result.decision.state == EntitlementState.CANCELED
    assert not result.decision.can_access


def test_provider_status_not_in_webhook_controls_access():
    result = run(provider=FakeProvider(snapshot("expired")),
                 evt=event("payment.succeeded"))
    assert not result.decision.can_access


@pytest.mark.parametrize("bad_event", ["wrong.type", "", "product.updated"])
def test_unknown_event_has_no_side_effects(bad_event):
    provider = FakeProvider(snapshot())
    repo = FakeRepo()
    result = run(provider=provider, repo=repo, evt=event(bad_event))
    assert not result.handled
    assert provider.lookups == 0 and not repo.writes


def test_bad_signature_never_fetches_subscription():
    provider = FakeProvider(snapshot())
    with pytest.raises(ValueError, match="signature"):
        run(provider=provider, signature_verified=False)
    assert provider.lookups == 0


def test_no_prebound_identity_never_fetches_subscription():
    repo = FakeRepo()
    repo.binding = None
    provider = FakeProvider(snapshot())
    with pytest.raises(ValueError, match="not bound"):
        run(provider=provider, repo=repo)
    assert provider.lookups == 0


@pytest.mark.parametrize("wrong", [
    {"merchant_id": "biz_other"},
    {"product_id": "prod_one_time"},
    {"customer_id": "cus_other"},
    {"checkout_plan_id": "plan_unapproved"},
    {"amount_usd_cents": 2700},
])
def test_bogus_provider_facts_never_write(wrong):
    repo = FakeRepo()
    with pytest.raises(ValueError):
        run(repo=repo, provider=FakeProvider(snapshot(**wrong)))
    assert not repo.writes


def test_provider_cannot_swap_subscription_identity():
    with pytest.raises(ValueError, match="identity"):
        run(provider=FakeProvider(snapshot(subscription_id="sub_other")))


def test_replayed_older_event_cannot_restore_access():
    repo = FakeRepo()
    provider = FakeProvider(snapshot("canceled", observed_at=NOW + timedelta(minutes=5)))
    run(repo=repo, provider=provider)
    provider.current = snapshot("active")
    with pytest.raises(ValueError):
        run(repo=repo, provider=provider)
    assert len(repo.writes) == 1
