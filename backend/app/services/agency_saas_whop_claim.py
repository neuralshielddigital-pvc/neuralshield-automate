"""Secure, default-deny first binding of a Whop SaaS subscription to a tenant.

This is a library service, NOT a public endpoint. The caller MUST authenticate
the SaaS user and obtain a provider-backed proof that this very authenticated
user authorized linking the provider identity. Possession of a subscription ID,
a checkout email, a redirect URL, or even a signed webhook is NOT ownership
proof. No binding, webhook or checkout response grants paid access.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol

from app.services.agency_saas_whop_guardrails import (
    RecurringPlan, VerifiedSubscriptionFacts, validate_recurring_snapshot,
)
from app.services.agency_saas_whop_lifecycle import (
    AccountBinding, WhopSubscriptionProvider,
)


@dataclass(frozen=True)
class AuthenticatedSaasPrincipal:
    user_id: str
    tenant_id: str
    account_active: bool
    email_verified: bool
    tenant_authorized: bool


@dataclass(frozen=True)
class ProviderOwnershipProof:
    """Result of a separate trusted provider authorization flow.

    An API request body MUST NEVER be deserialized directly into this object
    and treated as a verified proof. The caller must establish the provenance,
    nonce/session binding, replay protection and expiry of the provider proof.
    """
    subscription_id: str
    customer_id: str
    authorized_user_id: str
    authorized_tenant_id: str
    verified_by_provider: bool
    verified_for_session: bool


def _valid_binding_identity(value: object) -> bool:
    """Reject control characters, ambiguous whitespace and unbounded identities."""
    return (
        isinstance(value, str)
        and 0 < len(value) <= 128
        and value == value.strip()
        and all(33 <= ord(char) <= 126 for char in value)
    )


class FirstBindingWriter(Protocol):
    def create_binding_if_absent(self, binding: AccountBinding) -> bool:
        """Atomic unique insert or exact-owner idempotent replay.

        Must raise on a subscription claimed by another principal. It MUST
        initialize disabled access; false means exact same binding exists.
        """
        ...


@dataclass(frozen=True)
class ClaimResult:
    newly_bound: bool
    subscription_id: str


def bind_verified_saas_subscription(
    *,
    principal: AuthenticatedSaasPrincipal,
    proof: ProviderOwnershipProof,
    provider: WhopSubscriptionProvider,
    repository: FirstBindingWriter,
    allowed_plans: Mapping[str, RecurringPlan],
    expected_merchant_id: str,
) -> ClaimResult:
    """Only bind authorized, verified users; never grant paid entitlements.

    This deliberately does not create an OAuth callback or invite link.
    Provider ownership authorization must be implemented and independently
    tested before any endpoint is permitted to invoke this function.
    """
    if (
        principal.account_active is not True or principal.email_verified is not True
        or principal.tenant_authorized is not True
        or not _valid_binding_identity(principal.user_id)
        or not _valid_binding_identity(principal.tenant_id)
    ):
        raise ValueError("SaaS principal is not authorized to claim a subscription")
    if (
        proof.verified_by_provider is not True or proof.verified_for_session is not True
        or not _valid_binding_identity(proof.authorized_user_id)
        or not _valid_binding_identity(proof.authorized_tenant_id)
        or proof.authorized_user_id != principal.user_id
        or proof.authorized_tenant_id != principal.tenant_id
        or not _valid_binding_identity(proof.subscription_id)
        or not _valid_binding_identity(proof.customer_id)
    ):
        raise ValueError("Missing verified customer-to-session ownership proof")
    snapshot: VerifiedSubscriptionFacts = provider.retrieve_verified_subscription(
        proof.subscription_id
    )
    if (
        snapshot.subscription_id != proof.subscription_id
        or snapshot.customer_id != proof.customer_id
    ):
        raise ValueError("Provider subscription/customer ownership mismatch")
    # Validate the full merchant/product/plan/currency/interval/price contract.
    # This check produces a *decision*, but binding never grants that decision.
    validate_recurring_snapshot(
        snapshot=snapshot, independently_verified=True,
        expected_merchant_id=expected_merchant_id,
        allowed_plans=allowed_plans,
        bound_customer_id=proof.customer_id,
    )
    binding = AccountBinding(
        subscription_id=proof.subscription_id,
        provider_customer_id=proof.customer_id,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
    )
    newly_bound = repository.create_binding_if_absent(binding)
    return ClaimResult(newly_bound=newly_bound, subscription_id=proof.subscription_id)
