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


@pytest.mark.parametrize("failure_mode", ["immediate", "iteration"])
def test_candidate_source_outage_alerts_and_fails_closed(failure_mode):
    args = arguments()
    alert = Mock()

    def fail_immediately(**kwargs):
        raise ConnectionError("sensitive database connection details")

    def fail_during_iteration(**kwargs):
        yield "sub_test"
        raise ConnectionError("sensitive database connection details")

    args["candidates"].list_due_subscription_ids.side_effect = (
        fail_immediately if failure_mode == "immediate" else fail_during_iteration
    )
    with pytest.raises(RuntimeError, match="candidate enumeration failed") as err:
        run_monitored_paid_reconciliation(**args, alert_on_failure=alert)
    assert "sensitive" not in str(err.value)
    alert.assert_called_once_with(failed_subscription_ids=(), examined=0)
    args["provider"].retrieve_verified_subscription.assert_not_called()
    args["payment_provider"].retrieve_verified_first_charge.assert_not_called()
    args["repository"].apply_if_current.assert_not_called()


@pytest.mark.parametrize("candidate_ids", [
    ["sub_test", "sub_test"],
    ["sub_test", "invalid subscription"],
    [None],
    ["sub_test"] * 101,
])
def test_invalid_candidate_batch_alerts_and_prevents_provider_access(candidate_ids):
    args = arguments()
    args["candidates"].list_due_subscription_ids.return_value = candidate_ids
    alert = Mock()
    with pytest.raises(RuntimeError, match="candidate enumeration failed"):
        run_monitored_paid_reconciliation(**args, alert_on_failure=alert)
    alert.assert_called_once_with(failed_subscription_ids=(), examined=0)
    args["provider"].retrieve_verified_subscription.assert_not_called()
    args["payment_provider"].retrieve_verified_first_charge.assert_not_called()
    args["repository"].apply_if_current.assert_not_called()


@pytest.mark.parametrize("limit", [0, -1, True, False, 1.5, "100", None, 1001])
def test_invalid_scheduler_limit_alerts_before_candidate_or_provider_access(limit):
    args = arguments()
    alert = Mock()
    with pytest.raises(ValueError, match="batch limit"):
        run_monitored_paid_reconciliation(**args, alert_on_failure=alert, limit=limit)
    alert.assert_called_once_with(failed_subscription_ids=(), examined=0)
    args["candidates"].list_due_subscription_ids.assert_not_called()
    args["provider"].retrieve_verified_subscription.assert_not_called()
    args["payment_provider"].retrieve_verified_first_charge.assert_not_called()
    args["repository"].apply_if_current.assert_not_called()
