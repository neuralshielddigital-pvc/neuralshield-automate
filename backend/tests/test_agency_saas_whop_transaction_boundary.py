"""Transaction boundary regression: never redeem ownership with a foreign writer.

No Whop requests, payments, or production database connections.
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


@pytest.mark.parametrize("foreign_writer", [False, True])
def test_transactional_claim_rejects_untrusted_or_foreign_session_writer(foreign_writer):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    nonces.metadata.create_all(engine)
    now = datetime(2026, 11, 23, tzinfo=timezone.utc)
    user_id, tenant_id = str(uuid4()), str(uuid4())
    nonce = "nonce-" + uuid4().hex
    session_id = "session-" + uuid4().hex

    class Forbidden:
        def __getattr__(self, name):
            raise AssertionError("Untrusted writer reached provider verification")

    with Session(engine) as db, Session(engine) as other_db:
        db.execute(nonces.insert().values(
            nonce=nonce, session_id=session_id, user_id=user_id,
            tenant_id=tenant_id, expires_at=now + timedelta(minutes=5),
            consumed_at=None,
        ))
        db.commit()
        writer = (SQLAlchemyWhopSaasBindingRepository(other_db)
                  if foreign_writer else Forbidden())
        with pytest.raises(ValueError, match="transactional SQLAlchemy repository|share a transaction"):
            claim_with_persistent_authorization(
                db=db, nonce_table=nonces,
                principal=AuthenticatedSaasPrincipal(
                    user_id=user_id, tenant_id=tenant_id,
                    account_active=True, email_verified=True,
                    tenant_authorized=True,
                ),
                session_id=session_id, nonce=nonce,
                authorization_response={}, verifier=Forbidden(),
                provider=Forbidden(), repository=writer,
                allowed_plans={}, expected_merchant_id="biz_test", now=now,
            )
        assert db.execute(
            select(nonces.c.consumed_at).where(nonces.c.nonce == nonce)
        ).scalar_one() is None
    engine.dispose()
