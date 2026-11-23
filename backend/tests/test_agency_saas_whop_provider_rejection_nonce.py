"""Regression: SQLite must fail closed when it loses nonce timezone information.

SQLite returns naive datetimes even for timezone-aware columns. Unlike PostgreSQL,
this fixture cannot exercise provider rejection after successful nonce validation.
The production authorization gate must reject the naive timestamp without
calling a verifier or consuming the nonce. No network or production writes.
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.services.agency_saas_whop_claim import AuthenticatedSaasPrincipal
from app.services.agency_saas_whop_nonce_table import whop_saas_ownership_nonces as nonces
from app.services.agency_saas_whop_repository import SQLAlchemyWhopSaasBindingRepository
from app.services.agency_saas_whop_transactional_claim import claim_with_persistent_authorization


def test_sqlite_naive_expiry_fails_closed_without_consuming_nonce():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    nonces.metadata.create_all(engine)
    now = datetime(2026, 11, 23, tzinfo=timezone.utc)
    user_id, tenant_id = str(uuid4()), str(uuid4())
    nonce, session_id = "nonce-" + uuid4().hex, "session-" + uuid4().hex

    class RejectingVerifier:
        calls = 0

        def verify_authorization(self, *, authorization_response, pending):
            self.calls += 1
            raise ValueError("Provider authorization rejected")

    class ForbiddenProvider:
        def retrieve_verified_subscription(self, subscription_id):
            raise AssertionError("Unverified proof reached subscription provider")

    verifier = RejectingVerifier()
    with Session(engine) as db:
        db.execute(nonces.insert().values(
            nonce=nonce, session_id=session_id, user_id=user_id,
            tenant_id=tenant_id, expires_at=now + timedelta(minutes=5),
            consumed_at=None,
        ))
        db.commit()
        with pytest.raises(ValueError, match="Invalid or expired session-bound authorization"):
            claim_with_persistent_authorization(
                db=db, nonce_table=nonces,
                principal=AuthenticatedSaasPrincipal(
                    user_id=user_id, tenant_id=tenant_id,
                    account_active=True, email_verified=True,
                    tenant_authorized=True,
                ),
                session_id=session_id, nonce=nonce,
                authorization_response={"untrusted": "payload"},
                verifier=verifier, provider=ForbiddenProvider(),
                repository=SQLAlchemyWhopSaasBindingRepository(db),
                allowed_plans={}, expected_merchant_id="biz_test", now=now,
            )
        assert verifier.calls == 0
        assert db.execute(
            select(nonces.c.consumed_at).where(nonces.c.nonce == nonce)
        ).scalar_one() is None
    engine.dispose()
