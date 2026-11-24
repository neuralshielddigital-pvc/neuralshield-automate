"""One-time, session-bound authorization gate for SaaS Whop ownership claims.

This is an internal service, not an HTTP callback. Provider authorization must
be independently verified by a trusted adapter before a proof is accepted.
The nonce store MUST implement an atomic compare-and-consume operation shared
across workers (for example a transactional SQL UPDATE with a unique nonce).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from app.services.agency_saas_whop_claim import (
    AuthenticatedSaasPrincipal,
    ProviderOwnershipProof,
)


@dataclass(frozen=True)
class PendingOwnershipAuthorization:
    nonce: str
    session_id: str
    user_id: str
    tenant_id: str
    expires_at: datetime


class AtomicAuthorizationStore(Protocol):
    def consume_if_matches(
        self, *, nonce: str, session_id: str, user_id: str,
        tenant_id: str, now: datetime,
    ) -> bool:
        """Atomically consume an unexpired, unused record matching all fields."""
        ...


def _safe_identifier(value: object, *, minimum: int = 1, maximum: int = 256) -> bool:
    return (
        isinstance(value, str)
        and minimum <= len(value) <= maximum
        and value == value.strip()
        and not any(ord(char) < 32 or ord(char) == 127 for char in value)
    )


class TrustedProviderProofVerifier(Protocol):
    def verify_authorization(
        self, *, authorization_response: object,
        pending: PendingOwnershipAuthorization,
    ) -> ProviderOwnershipProof:
        """Verify provider signature/token and subscription/customer provenance.

        Must not trust caller-supplied subscription or customer IDs alone.
        """
        ...


def redeem_ownership_authorization(
    *, principal: AuthenticatedSaasPrincipal,
    session_id: str,
    pending: PendingOwnershipAuthorization,
    authorization_response: object,
    verifier: TrustedProviderProofVerifier,
    store: AtomicAuthorizationStore,
    now: datetime | None = None,
) -> ProviderOwnershipProof:
    """Fail closed; never grant paid access or create subscription bindings."""
    instant = now if now is not None else datetime.now(timezone.utc)
    if (
        not isinstance(instant, datetime) or instant.tzinfo is None
        or instant.utcoffset() is None
    ):
        raise ValueError("An aware clock is required")
    if not isinstance(principal, AuthenticatedSaasPrincipal):
        raise ValueError("Invalid SaaS principal")
    if not isinstance(pending, PendingOwnershipAuthorization):
        raise ValueError("Invalid pending authorization")
    if (
        principal.account_active is not True
        or principal.email_verified is not True
        or principal.tenant_authorized is not True
        or not _safe_identifier(session_id, minimum=16)
        or not _safe_identifier(pending.session_id, minimum=16)
        or not _safe_identifier(principal.user_id)
        or not _safe_identifier(principal.tenant_id)
        or pending.session_id != session_id
        or pending.user_id != principal.user_id
        or pending.tenant_id != principal.tenant_id
        or not _safe_identifier(pending.nonce, minimum=16)
        or not isinstance(pending.expires_at, datetime)
        or pending.expires_at.tzinfo is None
        or pending.expires_at.utcoffset() is None
        or pending.expires_at <= instant
    ):
        raise ValueError("Invalid or expired session-bound authorization")
    # The verifier must independently authenticate the provider's authorization
    # response. Never consume the nonce for an unverified provider response.
    proof = verifier.verify_authorization(
        authorization_response=authorization_response, pending=pending,
    )
    if (
        not isinstance(proof, ProviderOwnershipProof)
        or proof.verified_by_provider is not True
        or proof.verified_for_session is not True
        or proof.authorized_user_id != principal.user_id
        or proof.authorized_tenant_id != principal.tenant_id
        or not _safe_identifier(proof.subscription_id)
        or not _safe_identifier(proof.customer_id)
    ):
        raise ValueError("Provider ownership verification failed")
    consumed = store.consume_if_matches(
        nonce=pending.nonce, session_id=session_id,
        user_id=principal.user_id, tenant_id=principal.tenant_id,
        now=instant,
    )
    if consumed is not True:
        raise ValueError("Authorization already consumed, expired or mismatched")
    return proof
