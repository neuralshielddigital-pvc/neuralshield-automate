"""Contract tests for the strict paid reconciliation scheduler boundary."""
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from app.services.agency_saas_whop_monitored_job import run_monitored_paid_reconciliation

NOW = datetime.now(timezone.utc)


def arguments():
    return dict(
        provider=Mock(),
        payment_provider=Mock(),
        repository=Mock(),
        candidates=Mock(list_due_subscription_ids=Mock(return_value=[])),
        expected_merchant_id="biz_test",
        allowed_plans={"plan_test": __import__(
            "app.services.agency_saas_whop_guardrails", fromlist=["RecurringPlan"]
        ).RecurringPlan("prod_test", "plan_test", "starter", 1900)},
        due_before=NOW,
    )


def test_missing_alert_sink_fails_before_provider_or_candidate_access():
    args = arguments()
    with pytest.raises(ValueError, match="alert sink"):
        run_monitored_paid_reconciliation(**args, alert_on_failure=None)
    args["provider"].retrieve_verified_subscription.assert_not_called()
    args["candidates"].list_due_subscription_ids.assert_not_called()


def test_empty_batch_reports_success_without_provider_calls():
    args = arguments()
    result = run_monitored_paid_reconciliation(**args, alert_on_failure=Mock())
    assert result.examined == result.failed == result.updated == 0
    args["provider"].retrieve_verified_subscription.assert_not_called()


def test_failed_candidate_is_alerted_and_job_fails():
    args = arguments()
    args["candidates"].list_due_subscription_ids.return_value = ["sub_test"]
    args["repository"].get_binding.return_value = None
    alert = Mock()
    with pytest.raises(RuntimeError, match="failed for 1 subscriptions"):
        run_monitored_paid_reconciliation(**args, alert_on_failure=alert)
    alert.assert_called_once_with(
        failed_subscription_ids=("sub_test",), examined=1
    )
    args["payment_provider"].retrieve_verified_first_charge.assert_not_called()
