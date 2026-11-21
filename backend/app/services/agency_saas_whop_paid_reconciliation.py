"""Fail-closed payment-backed reconciliation entrypoint.

This wrapper is the only reconciliation entrypoint eligible for a production
scheduler. Legacy reconciliation remains staging-only until callers migrate.
No Whop endpoint or response shape is assumed.
"""
from __future__ import annotations

from typing import Protocol

from app.services.agency_saas_whop_first_charge import VerifiedFirstCharge
from app.services.agency_saas_whop_period_payment import validate_period_payment
from app.services.agency_saas_whop_guardrails import validate_recurring_snapshot
from app.services.agency_saas_whop_paid_decision import validate_paid_recurring_snapshot
from app.services.agency_saas_whop_reconciliation import (
    ReconciliationReport, reconcile_due_whop_saas_subscriptions,
)


class VerifiedPaymentProvider(Protocol):
    def retrieve_verified_first_charge(self, subscription_id: str) -> VerifiedFirstCharge: ...


def reconcile_due_paid_whop_saas_subscriptions(
    *, payment_provider: VerifiedPaymentProvider, period_payment_provider=None,
    entitlement_period_provider=None, require_period_payment=False, **kwargs
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
    if (period_payment_provider is None) != (entitlement_period_provider is None):
        raise ValueError("Period payment and entitlement period providers must be configured together")
    if require_period_payment is True and period_payment_provider is None:
        raise ValueError("Production reconciliation requires verified billing-period payment evidence")
    if period_payment_provider is not None and not callable(
        getattr(period_payment_provider, "retrieve_verified_period_payment", None)
    ):
        raise ValueError("Verified billing-period payment provider is required")
    if entitlement_period_provider is not None and not callable(
        getattr(entitlement_period_provider, "retrieve_verified_entitlement_period", None)
    ):
        raise ValueError("Verified entitlement-period provider is required")
    provider = kwargs.get("provider")
    if provider is None or not callable(
        getattr(provider, "retrieve_verified_subscription", None)
    ):
        raise ValueError("Verified Whop subscription provider is required")

    repository = kwargs.get("repository")
    candidates = kwargs.get("candidates")
    if repository is None or not all(
        callable(getattr(repository, method, None))
        for method in ("get_binding", "get_decision", "apply_if_current")
    ):
        raise ValueError("Bound SaaS subscription repository is required")
    if candidates is None or not callable(
        getattr(candidates, "list_due_subscription_ids", None)
    ):
        raise ValueError("Bounded reconciliation candidate source is required")

    # Existing reconciliation performs binding checks and handles individual
    # failures. This adapter checks the first charge before the active
    # snapshot can reach that implementation's entitlement write.
    class PaymentGuardedProvider:
        def __init__(self):
            self.verified_snapshots = {}

        def retrieve_verified_subscription(self, subscription_id):
            # The lifecycle must write the exact subscription facts whose
            # payment was checked, not a second provider response.
            if subscription_id in self.verified_snapshots:
                return self.verified_snapshots[subscription_id]
            snapshot = provider.retrieve_verified_subscription(subscription_id)
            # Let legacy reconciliation reject malformed snapshots safely.
            from app.services.agency_saas_whop_guardrails import VerifiedSubscriptionFacts
            if not isinstance(snapshot, VerifiedSubscriptionFacts):
                return snapshot
            if isinstance(snapshot.provider_status, str) and snapshot.provider_status.lower() == "active":
                binding = kwargs["repository"].get_binding(subscription_id)
                if (binding is None or binding.subscription_id != subscription_id
                        or not isinstance(binding.tenant_id, str) or not binding.tenant_id.strip()
                        or not isinstance(binding.user_id, str) or not binding.user_id.strip()
                        or not isinstance(binding.provider_customer_id, str)
                        or not binding.provider_customer_id.strip()):
                    raise ValueError("Missing authorized subscription binding")
                # Reject invalid subscription identity, ownership, plan and price
                # before fetching any payment record.
                preliminary = validate_recurring_snapshot(
                    snapshot=snapshot,
                    independently_verified=True,
                    expected_merchant_id=kwargs["expected_merchant_id"],
                    allowed_plans=kwargs["allowed_plans"],
                    bound_customer_id=binding.provider_customer_id,
                    previous=kwargs["repository"].get_decision(subscription_id),
                )
                if not preliminary.can_access:
                    return snapshot
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
                if period_payment_provider is not None:
                    # Upstream adapters must authenticate both provider records.
                    period = entitlement_period_provider.retrieve_verified_entitlement_period(subscription_id)
                    if not isinstance(period, tuple) or len(period) != 2:
                        raise ValueError("Missing authenticated entitlement period")
                    evidence = period_payment_provider.retrieve_verified_period_payment(subscription_id)
                    validate_period_payment(
                        evidence=evidence, independently_verified=True,
                        subscription_id=subscription_id,
                        customer_id=binding.provider_customer_id,
                        merchant_id=kwargs["expected_merchant_id"],
                        expected_amount_usd_cents=snapshot.amount_usd_cents,
                        entitlement_start=period[0], entitlement_end=period[1],
                    )
            self.verified_snapshots[subscription_id] = snapshot
            return snapshot

    return reconcile_due_whop_saas_subscriptions(
        **{**kwargs, "provider": PaymentGuardedProvider()}
    )
