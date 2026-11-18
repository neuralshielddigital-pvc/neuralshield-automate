"""Synthetic scheduler alert-contract tests; no provider network or production DB."""
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.services.agency_saas_whop_guardrails import RecurringPlan
from app.services.agency_saas_whop_reconciliation import reconcile_due_whop_saas_subscriptions

PLAN = RecurringPlan("prod_synthetic", "plan_synthetic", "starter", 1900)
NOW = datetime(2026, 11, 18, tzinfo=timezone.utc)


class Candidates:
    def list_due_subscription_ids(self, *, before, limit):
        return ["sub_failure", "sub_missing"]


class Repository:
    def get_binding(self, subscription_id):
        if subscription_id == "sub_missing":
            return None
        return SimpleNamespace(
            subscription_id=subscription_id, tenant_id="tenant_synthetic",
            user_id="user_synthetic", provider_customer_id="cus_synthetic",
        )

    def get_decision(self, subscription_id):
        raise AssertionError("Failed provider lookup must not read a decision")

    def apply_if_current(self, binding, decision):
        raise AssertionError("Failed provider lookup must not update entitlement")


class Provider:
    def __init__(self):
        self.lookups = []

    def retrieve_verified_subscription(self, subscription_id):
        self.lookups.append(subscription_id)
        raise TimeoutError("SECRET_PROVIDER_TOKEN_DO_NOT_LOG")


def reconcile(provider, *, alert=None, strict=False):
    return reconcile_due_whop_saas_subscriptions(
        provider=provider, repository=Repository(), candidates=Candidates(),
        expected_merchant_id="biz_synthetic",
        allowed_plans={PLAN.checkout_plan_id: PLAN},
        due_before=NOW, alert_on_failure=alert, raise_on_failure=strict,
    )


def test_partial_failure_reports_only_subscription_ids_without_provider_exception():
    provider = Provider()
    alerts = []
    report = reconcile(
        provider,
        alert=lambda *, failed_subscription_ids, examined:
            alerts.append((failed_subscription_ids, examined)),
    )
    assert provider.lookups == ["sub_failure"]
    assert report.failed == 2 and report.updated == 0
    assert report.failed_subscription_ids == ("sub_failure", "sub_missing")
    assert alerts == [(("sub_failure", "sub_missing"), 2)]
    assert "SECRET_PROVIDER_TOKEN" not in repr(report)


def test_strict_scheduler_failure_is_sanitized_after_alert_delivery():
    provider = Provider()
    alerts = []
    with pytest.raises(RuntimeError, match="failed for 2 subscriptions") as exc:
        reconcile(
            provider, strict=True,
            alert=lambda *, failed_subscription_ids, examined:
                alerts.append((failed_subscription_ids, examined)),
        )
    assert alerts == [(("sub_failure", "sub_missing"), 2)]
    assert "SECRET_PROVIDER_TOKEN" not in str(exc.value)


def test_strict_scheduler_failure_without_alert_sink_still_fails_closed():
    with pytest.raises(RuntimeError, match="failed for 2 subscriptions") as exc:
        reconcile(Provider(), strict=True)
    assert "SECRET_PROVIDER_TOKEN" not in str(exc.value)
