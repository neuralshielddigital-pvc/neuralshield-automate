"""Isolated nonce issuance tests: no provider calls or paid entitlement."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.services.agency_saas_whop_claim import AuthenticatedSaasPrincipal
from app.services.agency_saas_whop_nonce_issuer import create_pending_ownership_authorization
from app.services.agency_saas_whop_nonce_table import whop_saas_ownership_nonces as table
from app.services.agency_saas_whop_sql_nonce_store import SQLAlchemyAtomicAuthorizationStore

NOW = datetime(2026, 11, 22, tzinfo=timezone.utc)
SESSION = "session-01234567890123456789"


def principal(**overrides):
    fields = dict(user_id="user-1", tenant_id="tenant-1", account_active=True,
                  email_verified=True, tenant_authorized=True)
    fields.update(overrides)
    return AuthenticatedSaasPrincipal(**fields)


def test_nonce_is_random_persisted_and_single_use():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    table.metadata.create_all(engine)
    with Session(engine) as db:
        first = create_pending_ownership_authorization(
            db=db, table=table, principal=principal(), session_id=SESSION, now=NOW)
        second = create_pending_ownership_authorization(
            db=db, table=table, principal=principal(), session_id=SESSION, now=NOW)
        assert first.nonce != second.nonce
        assert len(first.nonce) >= 40
        assert first.expires_at == NOW + timedelta(minutes=10)
        db.commit()
    with Session(engine) as db:
        assert set(db.execute(select(table.c.nonce)).scalars().all()) == {first.nonce, second.nonce}
        store = SQLAlchemyAtomicAuthorizationStore(db, table)
        args = dict(nonce=first.nonce, session_id=SESSION,
                    user_id="user-1", tenant_id="tenant-1", now=NOW)
        assert store.consume_if_matches(**args)
        assert not store.consume_if_matches(**args)
        assert not store.consume_if_matches(**{**args, "nonce": second.nonce, "tenant_id": "other"})
        assert not store.consume_if_matches(**{**args, "nonce": second.nonce, "now": NOW + timedelta(minutes=11)})


@pytest.mark.parametrize("changes", [
    {"account_active": False}, {"email_verified": False},
    {"tenant_authorized": False}, {"tenant_id": " "},
])
def test_ineligible_principal_cannot_create_nonce(changes):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    table.metadata.create_all(engine)
    with Session(engine) as db:
        with pytest.raises(ValueError):
            create_pending_ownership_authorization(
                db=db, table=table, principal=principal(**changes),
                session_id=SESSION, now=NOW)
        assert db.execute(select(table.c.nonce)).first() is None


@pytest.mark.parametrize("ttl", [0, 59, 901, True])
def test_invalid_ttl_rejected(ttl):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    table.metadata.create_all(engine)
    with Session(engine) as db:
        with pytest.raises(ValueError):
            create_pending_ownership_authorization(
                db=db, table=table, principal=principal(),
                session_id=SESSION, now=NOW, ttl_seconds=ttl)
