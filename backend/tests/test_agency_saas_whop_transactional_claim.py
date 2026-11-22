"""Fail-closed tests for the transactional authorization-to-binding bridge."""
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.services.agency_saas_whop_claim import AuthenticatedSaasPrincipal
from app.services.agency_saas_whop_nonce_table import whop_saas_ownership_nonces as table
from app.services.agency_saas_whop_transactional_claim import claim_with_persistent_authorization

NOW = datetime(2026, 11, 23, tzinfo=timezone.utc)


def test_unknown_nonce_does_not_call_provider_or_create_binding():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    table.metadata.create_all(engine)
    class Forbidden:
        def __getattr__(self, name):
            raise AssertionError("Unverified authorization reached external dependency")
    with Session(engine) as db:
        with pytest.raises(ValueError, match="Unknown authorization nonce"):
            claim_with_persistent_authorization(
                db=db, nonce_table=table,
                principal=AuthenticatedSaasPrincipal(
                    user_id="user", tenant_id="tenant", account_active=True,
                    email_verified=True, tenant_authorized=True),
                session_id="session-01234567890123456789",
                nonce="nonexistent-01234567890123456789",
                authorization_response={}, verifier=Forbidden(),
                provider=Forbidden(), repository=Forbidden(),
                allowed_plans={}, expected_merchant_id="biz_test", now=NOW,
            )
        assert db.execute(select(table.c.nonce)).first() is None


@pytest.mark.parametrize("nonce", ["", "short", None])
def test_invalid_nonce_rejected_before_database_lookup(nonce):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    table.metadata.create_all(engine)
    with Session(engine) as db:
        with pytest.raises(ValueError, match="Invalid authorization nonce"):
            claim_with_persistent_authorization(
                db=db, nonce_table=table, principal=None, session_id="",
                nonce=nonce, authorization_response=None, verifier=None,
                provider=None, repository=None, allowed_plans={},
                expected_merchant_id="", now=NOW,
            )
