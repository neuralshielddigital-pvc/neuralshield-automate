"""Transactional bridge from authenticated SaaS session to a verified Whop binding.

Not an HTTP endpoint. A trusted provider authorization adapter and an authenticated
SaaS session are mandatory. The caller owns commit/rollback; never commit nonce
consumption separately from the subscription binding.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Table, select
from sqlalchemy.orm import Session

from app.services.agency_saas_whop_authorization_gate import (
    PendingOwnershipAuthorization, TrustedProviderProofVerifier,
    redeem_ownership_authorization,
)
from app.services.agency_saas_whop_claim import (
    AuthenticatedSaasPrincipal, FirstBindingWriter,
    bind_verified_saas_subscription,
)
from app.services.agency_saas_whop_guardrails import RecurringPlan
from app.services.agency_saas_whop_lifecycle import WhopSubscriptionProvider
from app.services.agency_saas_whop_sql_nonce_store import SQLAlchemyAtomicAuthorizationStore


def claim_with_persistent_authorization(
    *, db: Session, nonce_table: Table, principal: AuthenticatedSaasPrincipal,
    session_id: str, nonce: str, authorization_response: object,
    verifier: TrustedProviderProofVerifier, provider: WhopSubscriptionProvider,
    repository: FirstBindingWriter, allowed_plans: dict[str, RecurringPlan],
    expected_merchant_id: str, now: datetime | None = None,
):
    """Validate, atomically consume nonce, and insert disabled binding.

    Call only with a server-authenticated principal and session identifier.
    The caller MUST rollback the whole transaction on any exception and commit
    only after this function returns. The repository MUST share this db
    transaction; otherwise atomicity is not guaranteed.
    """
    instant = now if now is not None else datetime.now(timezone.utc)
    if not isinstance(nonce, str) or not 16 <= len(nonce) <= 256:
        raise ValueError("Invalid authorization nonce")
    if not isinstance(instant, datetime) or instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("Aware clock required")
    record = db.execute(
        select(nonce_table).where(nonce_table.c.nonce == nonce)
    ).mappings().one_or_none()
    if record is None:
        raise ValueError("Unknown authorization nonce")
    pending = PendingOwnershipAuthorization(
        nonce=record["nonce"], session_id=record["session_id"],
        user_id=record["user_id"], tenant_id=record["tenant_id"],
        expires_at=record["expires_at"],
    )
    store = SQLAlchemyAtomicAuthorizationStore(db, nonce_table)
    proof = redeem_ownership_authorization(
        principal=principal, session_id=session_id, pending=pending,
        authorization_response=authorization_response, verifier=verifier,
        store=store, now=instant,
    )
    return bind_verified_saas_subscription(
        principal=principal, proof=proof, provider=provider,
        repository=repository, allowed_plans=allowed_plans,
        expected_merchant_id=expected_merchant_id,
    )
