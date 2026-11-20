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
