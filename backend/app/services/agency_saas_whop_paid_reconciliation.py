"""Fail-closed payment-backed reconciliation entrypoint.

This wrapper is the only reconciliation entrypoint eligible for a production
scheduler. Legacy reconciliation remains staging-only until callers migrate.
No Whop endpoint or response shape is assumed.
"""
from __future__ import annotations

from typing import Protocol

from app.services.agency_saas_whop_first_charge import VerifiedFirstCharge
from app.services.agency_saas_whop_paid_decision import validate_paid_recurring_snapshot
from app.services.agency_saas_whop_reconciliation import (
    ReconciliationReport, reconcile_due_whop_saas_subscriptions,
)


class VerifiedPaymentProvider(Protocol):
    def retrieve_verified_first_charge(self, subscription_id: str) -> VerifiedFirstCharge: ...


def reconcile_due_paid_whop_saas_subscriptions(
    *, payment_provider: VerifiedPaymentProvider, **kwargs
) -> ReconciliationReport:
    """Require independently authenticated payment evidence before access.

    Wrap the subscription provider rather than trusting a webhook payment ID.
    Non-active decisions still revoke without a payment API lookup. The
    provider adapter must be separately authenticated and verified.
    """
    if payment_provider is None or not callable(
        getattr(payment_provider, "retrieve_verified_first_charge", None)
    ):
        raise ValueError("Verified Whop payment provider is required")
    provider = kwargs.get("provider")
    if provider is None or not callable(
        getattr(provider, "retrieve_verified_subscription", None)
    ):
        raise ValueError("Verified Whop subscription provider is required")

    # Existing reconciliation performs binding checks and handles individual
    # failures. This adapter checks the first charge before the active
    # snapshot can reach that implementation's entitlement write.
    class PaymentGuardedProvider:
        def retrieve_verified_subscription(self, subscription_id):
            snapshot = provider.retrieve_verified_subscription(subscription_id)
            # Let legacy reconciliation reject malformed snapshots safely.
            from app.services.agency_saas_whop_guardrails import VerifiedSubscriptionFacts
            if not isinstance(snapshot, VerifiedSubscriptionFacts):
                return snapshot
            if snapshot.provider_status.lower() == "active":
                binding = kwargs["repository"].get_binding(subscription_id)
                if binding is None or binding.subscription_id != subscription_id:
                    raise ValueError("Missing authorized subscription binding")
                charge = payment_provider.retrieve_verified_first_charge(subscription_id)
                validate_paid_recurring_snapshot(
                    snapshot=snapshot,
                    charge=charge,
                    subscription_independently_verified=True,
                    charge_independently_verified=True,
                    expected_merchant_id=kwargs["expected_merchant_id"],
                    allowed_plans=kwargs["allowed_plans"],
                    bound_customer_id=binding.provider_customer_id,
                    previous=kwargs["repository"].get_decision(subscription_id),
                )
            return snapshot

    return reconcile_due_whop_saas_subscriptions(
        **{**kwargs, "provider": PaymentGuardedProvider()}
    )
