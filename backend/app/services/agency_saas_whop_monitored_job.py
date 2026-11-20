"""Strict scheduler boundary for Whop SaaS paid reconciliation.

This module does not install or start a scheduler. A deployment must supply
independently authenticated provider adapters and a durable alert sink.
No public checkout or production feature flag is enabled here.
"""
from __future__ import annotations

from datetime import datetime
from typing import Mapping

from app.services.agency_saas_whop_guardrails import RecurringPlan
from app.services.agency_saas_whop_paid_reconciliation import (
    VerifiedPaymentProvider, reconcile_due_paid_whop_saas_subscriptions,
)
from app.services.agency_saas_whop_reconciliation import (
    ReconciliationAlertSink, ReconciliationCandidates, ReconciliationReport,
)
from app.services.agency_saas_whop_lifecycle import (
    BoundSubscriptionRepository, WhopSubscriptionProvider,
)


def run_monitored_paid_reconciliation(
    *,
    provider: WhopSubscriptionProvider,
    payment_provider: VerifiedPaymentProvider,
    repository: BoundSubscriptionRepository,
    candidates: ReconciliationCandidates,
    expected_merchant_id: str,
    allowed_plans: Mapping[str, RecurringPlan],
    due_before: datetime,
    alert_on_failure: ReconciliationAlertSink,
    limit: int = 100,
) -> ReconciliationReport:
    """Fail closed if monitoring is missing or any subscription fails.

    The caller is responsible for scheduling, credentials, retry/backoff and
    external supervision. Never use the subscription-only reconciliation job
    to grant paid entitlements.
    """
    if not callable(alert_on_failure):
        raise ValueError("Monitored paid reconciliation requires an alert sink")
    return reconcile_due_paid_whop_saas_subscriptions(
        provider=provider,
        payment_provider=payment_provider,
        repository=repository,
        candidates=candidates,
        expected_merchant_id=expected_merchant_id,
        allowed_plans=allowed_plans,
        due_before=due_before,
        limit=limit,
        alert_on_failure=alert_on_failure,
        raise_on_failure=True,
    )
