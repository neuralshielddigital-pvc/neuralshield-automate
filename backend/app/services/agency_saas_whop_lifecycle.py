"""Provider-verified, account-bound Whop SaaS subscription event orchestration.

Staging-only component. The HTTP webhook endpoint must verify the original
Whop signature and check event identity *before* calling this service.
No production endpoint is connected to this component yet.

The provider adapter MUST retrieve fresh subscription facts over authenticated
server-to-server API, never trust the signed webhook's embedded status/plan.
All writes MUST be atomic, idempotent, and serialized by subscription ID.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol

from app.services.agency_saas_whop_guardrails import (
    RecurringPlan,
    SubscriptionDecision,
    VerifiedSubscriptionFacts,
    validate_recurring_snapshot,
)


ALLOWED_EVENTS = frozenset({
    # Match event labels actually offered in the merchant's Whop dashboard.
    # Event payload shapes and provider subscription retrieval remain gated
    # pending a verified official API contract and signed end-to-end fixtures.
    "membership.activated",
    "membership.deactivated",
    "membership.cancel_at_period_end_changed",
    "membership.updated",
    "payment.succeeded",
    "payment.failed",
    "refund.created",
    "refund.updated",
})


@dataclass(frozen=True)
class AuthenticatedWebhookReference:
    """Created only after signature and delivery identity have been checked."""

    event_id: str
    event_type: str
    subscription_id: str


@dataclass(frozen=True)
class AccountBinding:
    """Preexisting explicit tenant ↔ provider identity relationship."""

    subscription_id: str
    provider_customer_id: str
    tenant_id: str
    user_id: str


class WhopSubscriptionProvider(Protocol):
    def retrieve_verified_subscription(
        self, subscription_id: str
    ) -> VerifiedSubscriptionFacts:
        """Server-to-server authenticated snapshot of current provider state."""
        ...


class BoundSubscriptionRepository(Protocol):
    def get_binding(self, subscription_id: str) -> AccountBinding | None: ...
    def get_decision(self, subscription_id: str) -> SubscriptionDecision | None: ...

    def apply_if_current(
        self, binding: AccountBinding, decision: SubscriptionDecision
    ) -> bool:
        """Atomically compare state/timestamps and persist; False for replay.

        Implementations must serialize writes for the subscription and must
        reject conflicting same-time facts. They may not create a binding here.
        """
        ...


@dataclass(frozen=True)
class ProcessingResult:
    handled: bool
    changed: bool
    decision: SubscriptionDecision | None


def process_verified_subscription_event(
    *,
    event: AuthenticatedWebhookReference,
    signature_verified: bool,
    provider: WhopSubscriptionProvider,
    repository: BoundSubscriptionRepository,
    expected_merchant_id: str,
    allowed_plans: Mapping[str, RecurringPlan],
) -> ProcessingResult:
    """Apply only authoritative subscription state to a *prebound* SaaS tenant.

    The event provides a lookup reference, never a grant decision. For safety,
    unknown event types, missing bindings and bad signatures fail closed.
    The caller should use provider retries for temporary external failures.
    """
    if not signature_verified:
        raise ValueError("Webhook signature was not verified")
    if not event.event_id.strip() or not event.subscription_id.strip():
        raise ValueError("Missing event/subscription identity")
    if event.event_type not in ALLOWED_EVENTS:
        return ProcessingResult(handled=False, changed=False, decision=None)
    binding = repository.get_binding(event.subscription_id)
    if binding is None:
        # Do not auto-attach based on checkout email or a malicious customer ID.
        raise ValueError("Subscription is not bound to a SaaS tenant")
    if (
        binding.subscription_id != event.subscription_id
        or not binding.tenant_id.strip()
        or not binding.user_id.strip()
        or not binding.provider_customer_id.strip()
    ):
        raise ValueError("Invalid existing SaaS account binding")
    snapshot = provider.retrieve_verified_subscription(event.subscription_id)
    if snapshot.subscription_id != event.subscription_id:
        raise ValueError("Provider subscription identity mismatch")
    previous = repository.get_decision(event.subscription_id)
    decision = validate_recurring_snapshot(
        snapshot=snapshot,
        independently_verified=True,
        expected_merchant_id=expected_merchant_id,
        allowed_plans=allowed_plans,
        bound_customer_id=binding.provider_customer_id,
        previous=previous,
    )
    changed = repository.apply_if_current(binding, decision)
    return ProcessingResult(handled=True, changed=changed, decision=decision)
