"""Persist a new session-bound ownership nonce before a trusted authorization redirect.

This does not authorize Whop ownership, make an API request, or enable billing.
The caller must use an authenticated SaaS principal and an independently verified
session ID, then commit this insert before issuing a redirect.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import Table, insert
from sqlalchemy.orm import Session

from app.services.agency_saas_whop_authorization_gate import (
    PendingOwnershipAuthorization,
    _safe_identifier,
)
from app.services.agency_saas_whop_claim import AuthenticatedSaasPrincipal


def create_pending_ownership_authorization(
    *, db: Session, table: Table, principal: AuthenticatedSaasPrincipal,
    session_id: str, now: datetime | None = None, ttl_seconds: int = 600,
) -> PendingOwnershipAuthorization:
    """Insert a cryptographically random nonce in the caller's transaction.

    Caller commits before returning the nonce to the browser. Database unique
    constraint enforces collision safety; IntegrityError must abort the flow.
    """
    instant = now if now is not None else datetime.now(timezone.utc)
    if (
        not isinstance(instant, datetime) or instant.tzinfo is None
        or instant.utcoffset() is None
        or not isinstance(ttl_seconds, int) or isinstance(ttl_seconds, bool)
        or not 60 <= ttl_seconds <= 900
        or not isinstance(principal, AuthenticatedSaasPrincipal)
        or principal.account_active is not True
        or principal.email_verified is not True
        or principal.tenant_authorized is not True
        or not _safe_identifier(principal.user_id)
        or not _safe_identifier(principal.tenant_id)
        or not _safe_identifier(session_id, minimum=16)
    ):
        raise ValueError("Invalid authenticated ownership authorization request")
    required = {"nonce", "session_id", "user_id", "tenant_id", "expires_at", "consumed_at"}
    if not required.issubset(table.c.keys()) or not table.c.nonce.primary_key:
        raise ValueError("Invalid ownership nonce table")
    nonce = secrets.token_urlsafe(32)
    expires_at = instant + timedelta(seconds=ttl_seconds)
    db.execute(insert(table).values(
        nonce=nonce, session_id=session_id, user_id=principal.user_id,
        tenant_id=principal.tenant_id, expires_at=expires_at, consumed_at=None,
    ))
    return PendingOwnershipAuthorization(
        nonce=nonce, session_id=session_id, user_id=principal.user_id,
        tenant_id=principal.tenant_id, expires_at=expires_at,
    )
