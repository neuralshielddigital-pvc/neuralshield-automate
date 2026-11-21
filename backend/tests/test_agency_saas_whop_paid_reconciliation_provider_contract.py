"""Fail-closed contract tests for the production-eligible reconciliation wrapper.

These synthetic tests deliberately do not model undocumented Whop API fields.
"""
from unittest.mock import Mock

import pytest

from app.services.agency_saas_whop_paid_reconciliation import (
    reconcile_due_paid_whop_saas_subscriptions,
)


@pytest.mark.parametrize("payment_provider", [None, object(), Mock(retrieve_verified_first_charge=None)])
def test_missing_authenticated_payment_lookup_is_rejected_before_any_work(payment_provider):
    subscription_provider = Mock()
    with pytest.raises(ValueError, match="payment provider"):
        reconcile_due_paid_whop_saas_subscriptions(
            payment_provider=payment_provider, provider=subscription_provider
        )
    subscription_provider.retrieve_verified_subscription.assert_not_called()


@pytest.mark.parametrize("subscription_provider", [None, object(), Mock(retrieve_verified_subscription=None)])
def test_missing_authenticated_subscription_lookup_is_rejected_before_any_work(subscription_provider):
    payment_provider = Mock()
    with pytest.raises(ValueError, match="subscription provider"):
        reconcile_due_paid_whop_saas_subscriptions(
            payment_provider=payment_provider, provider=subscription_provider
        )
    payment_provider.retrieve_verified_first_charge.assert_not_called()


@pytest.mark.parametrize(
    "repository,candidates,expected_error",
    [
        (None, Mock(), "repository"),
        (object(), Mock(), "repository"),
        (Mock(get_binding=None), Mock(), "repository"),
        (Mock(), None, "candidate source"),
        (Mock(), object(), "candidate source"),
        (Mock(), Mock(list_due_subscription_ids=None), "candidate source"),
    ],
)
def test_missing_persistence_dependencies_fail_before_provider_calls(repository, candidates, expected_error):
    subscription_provider = Mock()
    payment_provider = Mock()
    with pytest.raises(ValueError, match=expected_error):
        reconcile_due_paid_whop_saas_subscriptions(
            payment_provider=payment_provider,
            provider=subscription_provider,
            repository=repository,
            candidates=candidates,
        )
    subscription_provider.retrieve_verified_subscription.assert_not_called()
    payment_provider.retrieve_verified_first_charge.assert_not_called()


@pytest.mark.parametrize("ambiguous_flag", [None, 0, 1, "false", "true", [], {}])
def test_ambiguous_period_payment_gate_is_rejected_before_provider_calls(ambiguous_flag):
    subscription_provider = Mock()
    payment_provider = Mock()
    with pytest.raises(ValueError, match="explicit boolean"):
        reconcile_due_paid_whop_saas_subscriptions(
            payment_provider=payment_provider,
            provider=subscription_provider,
            require_period_payment=ambiguous_flag,
        )
    subscription_provider.retrieve_verified_subscription.assert_not_called()
    payment_provider.retrieve_verified_first_charge.assert_not_called()
