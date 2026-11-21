"""Strict scheduler boundary for Whop SaaS paid reconciliation.

This module does not install or start a scheduler. A deployment must supply
independently authenticated provider adapters and a durable alert sink.
No public checkout or production feature flag is enabled here.
"""
from __future__ import annotations

from datetime import datetime
import re
from typing import Mapping


class _AlertedCandidateFailure(RuntimeError):
    """Sanitized failure after an upstream candidate-source alert."""


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
    if type(limit) is not int or not 1 <= limit <= 1000:
        # Reject unsafe scheduler configuration before reading candidates.
        # In particular, bool is an int subclass and must not pass here.
        alert_on_failure(failed_subscription_ids=(), examined=0)
        raise ValueError("Invalid monitored reconciliation batch limit")
    class AlertingCandidates:
        def list_due_subscription_ids(self, *, before, limit):
            try:
                # Materialize here: generators may fail while being consumed by
                # the reconciliation loop rather than at method invocation.
                from itertools import islice
                ids = list(islice(iter(candidates.list_due_subscription_ids(
                    before=before, limit=limit
                )), limit + 1))
                # Invalid or over-limit batches must page the supervisor too;
                # the underlying reconciler rejects these before its alert path.
                if (len(ids) > limit or any(
                    not isinstance(sid, str)
                    or re.fullmatch(r"[A-Za-z0-9_-]{1,128}", sid) is None
                    for sid in ids
                ) or len(set(ids)) != len(ids)):
                    raise ValueError("Invalid reconciliation candidate batch")
                return ids
            except Exception as exc:
                # A database outage before a candidate is enumerated must
                # still page monitoring; never leak SQL or credentials.
                alert_on_failure(failed_subscription_ids=(), examined=0)
                raise _AlertedCandidateFailure(
                    "Whop SaaS reconciliation candidate enumeration failed"
                ) from None

    return reconcile_due_paid_whop_saas_subscriptions(
        provider=provider,
        payment_provider=payment_provider,
        repository=repository,
        candidates=AlertingCandidates(),
        expected_merchant_id=expected_merchant_id,
        allowed_plans=allowed_plans,
        due_before=due_before,
        limit=limit,
        alert_on_failure=alert_on_failure,
        raise_on_failure=True,
    )
