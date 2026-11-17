"""Bounded SaaS subscription reconciliation using authoritative Whop snapshots.

This module is NOT a scheduled job. The provider interface MUST be backed by
a separately verified authenticated Whop subscription API client, and startup
must require configured merchant/plan allowlists. Never refresh from webhook
payloads or buyer-provided IDs.

Errors are reported per subscription; a failed lookup does not extend stale
paid access (the existing 24-hour usage-limit TTL applies independently).
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import islice
import re
from datetime import datetime, timezone
from typing import Callable, Mapping, Protocol, Sequence

from app.services.agency_saas_whop_guardrails import (
    RecurringPlan, VerifiedSubscriptionFacts, validate_recurring_snapshot,
)
from app.services.agency_saas_whop_lifecycle import (
    AccountBinding, BoundSubscriptionRepository, WhopSubscriptionProvider,
)


class ReconciliationAlertSink(Protocol):
    def __call__(self, *, failed_subscription_ids: tuple[str, ...], examined: int) -> None: ...


class ReconciliationCandidates(Protocol):
    def list_due_subscription_ids(
        self, *, before: datetime, limit: int
    ) -> Sequence[str]: ...


@dataclass(frozen=True)
class ReconciliationReport:
    examined: int
    updated: int
    unchanged: int
    failed: int
    failed_subscription_ids: tuple[str, ...]


def reconcile_due_whop_saas_subscriptions(
    *,
    provider: WhopSubscriptionProvider,
    repository: BoundSubscriptionRepository,
    candidates: ReconciliationCandidates,
    expected_merchant_id: str,
    allowed_plans: Mapping[str, RecurringPlan],
    due_before: datetime,
    limit: int = 100,
    alert_on_failure: ReconciliationAlertSink | None = None,
    raise_on_failure: bool = False,
) -> ReconciliationReport:
    """Refresh an explicitly bounded set of *already bound* subscriptions.

    Returns failed identities to enable structured alerting and retry.
    No webhook event is assumed and no binding is created.
    """
    if not isinstance(due_before, datetime) or due_before.tzinfo is None or due_before.utcoffset() is None:
        raise ValueError("Reconciliation cutoff must be timezone aware")
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1 or limit > 100:
        raise ValueError("Reconciliation limit must be between 1 and 100")
    if (
        not isinstance(expected_merchant_id, str)
        or re.fullmatch(r"biz_[A-Za-z0-9_-]{1,128}", expected_merchant_id) is None
        or not isinstance(allowed_plans, Mapping)
        or not allowed_plans
        or any(
            not isinstance(plan_id, str)
            or not isinstance(plan, RecurringPlan)
            or plan_id != plan.checkout_plan_id
            for plan_id, plan in allowed_plans.items()
        )
    ):
        raise ValueError("Whop SaaS provider configuration is not ready")
    # A misbehaving candidate source may return a generator instead of a bounded
    # SQL result. Consume at most limit + 1 entries to avoid unbounded memory use.
    ids = list(islice(iter(candidates.list_due_subscription_ids(before=due_before, limit=limit)), limit + 1))
    # Validate before deduplicating: unhashable or malformed IDs must never
    # trigger provider lookups or leak into scheduler logs.
    if len(ids) > limit or any(
        not isinstance(sid, str)
        or re.fullmatch(r"[A-Za-z0-9_-]{1,128}", sid) is None
        for sid in ids
    ) or len(set(ids)) != len(ids):
        raise ValueError("Invalid or unbounded reconciliation candidates")
    updated = unchanged = 0
    failures: list[str] = []
    for subscription_id in ids:
        try:
            binding = repository.get_binding(subscription_id)
            if (
                binding is None
                or binding.subscription_id != subscription_id
                or not binding.tenant_id.strip()
                or not binding.user_id.strip()
                or not binding.provider_customer_id.strip()
            ):
                raise ValueError("Missing authorized SaaS subscription binding")
            snapshot = provider.retrieve_verified_subscription(subscription_id)
            if not isinstance(snapshot, VerifiedSubscriptionFacts):
                raise ValueError("Provider returned an invalid verified subscription snapshot")
            if snapshot.subscription_id != subscription_id:
                raise ValueError("Provider subscription identity mismatch")
            decision = validate_recurring_snapshot(
                snapshot=snapshot,
                independently_verified=True,
                expected_merchant_id=expected_merchant_id,
                allowed_plans=allowed_plans,
                bound_customer_id=binding.provider_customer_id,
                previous=repository.get_decision(subscription_id),
            )
            if repository.apply_if_current(binding, decision):
                updated += 1
            else:
                unchanged += 1
        except Exception:
            # No provider credentials or buyer information in the report.
            # An external scheduler must alert and retry failed identities.
            failures.append(subscription_id)
    report = ReconciliationReport(
        examined=len(ids), updated=updated, unchanged=unchanged,
        failed=len(failures), failed_subscription_ids=tuple(failures),
    )
    if report.failed and alert_on_failure is not None:
        # Fail the job when alert delivery fails; never silently discard
        # reconciliation failures as a successful scheduled run.
        alert_on_failure(
            failed_subscription_ids=report.failed_subscription_ids,
            examined=report.examined,
        )
    if report.failed and raise_on_failure:
        # Scheduled invocations must be able to signal partial failure to the
        # supervisor, even when the alert sink successfully delivered a notice.
        # Never include customer identities or provider exceptions in the error.
        raise RuntimeError(f"Whop SaaS reconciliation failed for {report.failed} subscriptions")
    return report
