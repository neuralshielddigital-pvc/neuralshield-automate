"""Synthetic regression checks for payment-backed reconciliation entrypoint."""
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from app.services.agency_saas_whop_first_charge import VerifiedFirstCharge
from app.services.agency_saas_whop_guardrails import RecurringPlan, VerifiedSubscriptionFacts
from app.services.agency_saas_whop_paid_reconciliation import (
    reconcile_due_paid_whop_saas_subscriptions,
)

NOW = datetime.now(timezone.utc)
PLAN = RecurringPlan("prod_test", "plan_test", "starter", 1900)


class Candidates:
    def list_due_subscription_ids(self, *, before, limit):
        return ["sub_test"]


class Repo:
    def __init__(self):
        self.writes = []
    def get_binding(self, sid):
        return type("Binding", (), dict(
            subscription_id=sid, tenant_id="tenant", user_id="user",
            provider_customer_id="cus_test"))()
    def get_decision(self, sid):
        return None
    def apply_if_current(self, binding, decision):
        self.writes.append(decision)
        return True


def snapshot(status="active"):
    return VerifiedSubscriptionFacts(
        merchant_id="biz_test", product_id=PLAN.product_id,
        checkout_plan_id=PLAN.checkout_plan_id,
        subscription_id="sub_test", customer_id="cus_test",
        provider_status=status, amount_usd_cents=1900, currency="USD",
        billing_interval="month", observed_at=NOW,
    )


def charge(**changes):
    fields = dict(payment_id="pay_test", subscription_id="sub_test",
        customer_id="cus_test", merchant_id="biz_test", status="paid",
        amount_usd_cents=1900, currency="USD",
        paid_at=NOW - timedelta(minutes=5))
    fields.update(changes)
    return VerifiedFirstCharge(**fields)


def run(status="active", evidence=None, payment_provider=None):
    repo = Repo()
    provider = Mock()
    provider.retrieve_verified_subscription.return_value = snapshot(status)
    if payment_provider is None:
        payment_provider = Mock()
        payment_provider.retrieve_verified_first_charge.return_value = (
            evidence if evidence is not None else charge()
        )
    report = reconcile_due_paid_whop_saas_subscriptions(
        payment_provider=payment_provider, provider=provider,
        repository=repo, candidates=Candidates(),
        expected_merchant_id="biz_test",
        allowed_plans={PLAN.checkout_plan_id: PLAN},
        due_before=NOW,
    )
    return report, repo, payment_provider


def test_verified_charge_allows_active():
    report, repo, payment = run()
    assert report.updated == 1 and report.failed == 0
    assert repo.writes[0].can_access is True
    payment.retrieve_verified_first_charge.assert_called_once_with("sub_test")


@pytest.mark.parametrize("changes", [
    {"status": "failed"}, {"status": "refunded"},
    {"customer_id": "cus_other"}, {"subscription_id": "sub_other"},
    {"merchant_id": "biz_other"}, {"amount_usd_cents": 5900},
    {"currency": "EUR"}, {"paid_at": NOW + timedelta(days=1)},
])
def test_bad_payment_never_grants(changes):
    report, repo, _ = run(evidence=charge(**changes))
    assert report.failed == 1 and report.updated == 0
    assert repo.writes == []


def test_missing_payment_provider_fails_before_lookup():
    with pytest.raises(ValueError, match="payment provider"):
        reconcile_due_paid_whop_saas_subscriptions(
            payment_provider=None, provider=Mock()
        )


@pytest.mark.parametrize("status", ["canceled", "refunded", "expired"])
def test_revocation_does_not_depend_on_payment_api(status):
    payment = Mock()
    payment.retrieve_verified_first_charge.side_effect = RuntimeError("outage")
    report, repo, _ = run(status=status, payment_provider=payment)
    assert report.updated == 1 and repo.writes[0].can_access is False
    payment.retrieve_verified_first_charge.assert_not_called()


def test_payment_outage_does_not_refresh_active_access():
    payment = Mock()
    payment.retrieve_verified_first_charge.side_effect = RuntimeError("outage")
    report, repo, _ = run(payment_provider=payment)
    assert report.failed == 1 and repo.writes == []


def test_payment_outage_alerts_and_fails_scheduled_job():
    payment = Mock()
    payment.retrieve_verified_first_charge.side_effect = RuntimeError("provider unavailable")
    alerts = Mock()
    repository = Repo()
    provider = Mock()
    provider.retrieve_verified_subscription.return_value = snapshot("active")
    with pytest.raises(RuntimeError, match="failed for 1 subscriptions"):
        reconcile_due_paid_whop_saas_subscriptions(
            payment_provider=payment, provider=provider,
            repository=repository, candidates=Candidates(),
            expected_merchant_id="biz_test",
            allowed_plans={PLAN.checkout_plan_id: PLAN},
            due_before=NOW, alert_on_failure=alerts, raise_on_failure=True,
        )
    assert repository.writes == []
    alerts.assert_called_once_with(
        failed_subscription_ids=("sub_test",), examined=1,
    )


def test_payment_outage_alert_delivery_failure_is_not_silenced():
    payment = Mock()
    payment.retrieve_verified_first_charge.side_effect = RuntimeError("provider unavailable")
    alerts = Mock(side_effect=RuntimeError("alert transport unavailable"))
    with pytest.raises(RuntimeError, match="alert transport unavailable"):
        reconcile_due_paid_whop_saas_subscriptions(
            payment_provider=payment, provider=Mock(
                retrieve_verified_subscription=Mock(return_value=snapshot("active"))
            ),
            repository=Repo(), candidates=Candidates(),
            expected_merchant_id="biz_test",
            allowed_plans={PLAN.checkout_plan_id: PLAN},
            due_before=NOW, alert_on_failure=alerts, raise_on_failure=True,
        )


def test_unbound_subscription_never_fetches_payment_or_grants_access():
    class UnboundRepo(Repo):
        def get_binding(self, sid):
            return None

    repository = UnboundRepo()
    subscription_provider = Mock()
    subscription_provider.retrieve_verified_subscription.return_value = snapshot("active")
    payment_provider = Mock()
    report = reconcile_due_paid_whop_saas_subscriptions(
        payment_provider=payment_provider, provider=subscription_provider,
        repository=repository, candidates=Candidates(),
        expected_merchant_id="biz_test",
        allowed_plans={PLAN.checkout_plan_id: PLAN}, due_before=NOW,
    )
    assert report.failed == 1 and report.updated == 0
    assert repository.writes == []
    payment_provider.retrieve_verified_first_charge.assert_not_called()


def test_trialing_never_fetches_payment_or_grants_paid_access():
    payment_provider = Mock()
    report, repository, _ = run(status="trialing", payment_provider=payment_provider)
    assert report.failed == 0 and report.updated == 1
    assert repository.writes[0].can_access is False
    payment_provider.retrieve_verified_first_charge.assert_not_called()


@pytest.mark.parametrize("field,value", [
    ("customer_id", "cus_wrong"),
    ("merchant_id", "biz_wrong"),
    ("checkout_plan_id", "plan_wrong"),
    ("amount_usd_cents", 5900),
])
def test_invalid_active_subscription_never_queries_payment(field, value):
    from dataclasses import replace

    payment = Mock()
    repository = Repo()
    provider = Mock()
    provider.retrieve_verified_subscription.return_value = replace(snapshot("active"), **{field: value})
    report = reconcile_due_paid_whop_saas_subscriptions(
        payment_provider=payment, provider=provider,
        repository=repository, candidates=Candidates(),
        expected_merchant_id="biz_test",
        allowed_plans={PLAN.checkout_plan_id: PLAN}, due_before=NOW,
    )
    assert report.failed == 1 and report.updated == 0
    assert repository.writes == []
    payment.retrieve_verified_first_charge.assert_not_called()


@pytest.mark.parametrize("missing_field", ["tenant_id", "user_id", "provider_customer_id"])
@pytest.mark.parametrize("invalid_value", ["", "  ", None])
def test_incomplete_ownership_binding_never_fetches_payment(missing_field, invalid_value):
    class IncompleteRepo(Repo):
        def get_binding(self, sid):
            binding = super().get_binding(sid)
            setattr(binding, missing_field, invalid_value)
            return binding

    repository = IncompleteRepo()
    subscription_provider = Mock()
    subscription_provider.retrieve_verified_subscription.return_value = snapshot("active")
    payment_provider = Mock()
    report = reconcile_due_paid_whop_saas_subscriptions(
        payment_provider=payment_provider, provider=subscription_provider,
        repository=repository, candidates=Candidates(),
        expected_merchant_id="biz_test",
        allowed_plans={PLAN.checkout_plan_id: PLAN}, due_before=NOW,
    )
    assert report.failed == 1 and report.updated == 0
    assert repository.writes == []
    payment_provider.retrieve_verified_first_charge.assert_not_called()


def test_duplicate_candidate_lookup_does_not_switch_verified_snapshot():
    """An adapter must not substitute a second provider snapshot after charge check."""
    class DoubleLookupCandidates:
        def list_due_subscription_ids(self, *, before, limit):
            return ["sub_test"]

    provider = Mock()
    provider.retrieve_verified_subscription.side_effect = [
        snapshot("active"), snapshot("canceled")
    ]
    payment = Mock()
    payment.retrieve_verified_first_charge.return_value = charge()
    repo = Repo()
    report = reconcile_due_paid_whop_saas_subscriptions(
        payment_provider=payment, provider=provider, repository=repo,
        candidates=DoubleLookupCandidates(), expected_merchant_id="biz_test",
        allowed_plans={PLAN.checkout_plan_id: PLAN}, due_before=NOW,
    )
    assert report.updated == 1
    assert repo.writes[0].can_access is True
    provider.retrieve_verified_subscription.assert_called_once_with("sub_test")
