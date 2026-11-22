"""Regression: a nontransactional writer must never reach nonce redemption."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, insert, select
from sqlalchemy.orm import Session

from app.services.agency_saas_whop_claim import AuthenticatedSaasPrincipal
from app.services.agency_saas_whop_nonce_table import whop_saas_ownership_nonces as table
from app.services.agency_saas_whop_transactional_claim import claim_with_persistent_authorization

NOW = datetime(2026, 11, 23, tzinfo=timezone.utc)


def test_arbitrary_writer_rejected_without_consuming_nonce():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    table.metadata.create_all(engine)
    user_id, tenant_id = str(uuid4()), str(uuid4())
    nonce = "nonce-01234567890123456789"
    session_id = "session-01234567890123456789"
    with Session(engine) as db:
        db.execute(insert(table).values(
            nonce=nonce, session_id=session_id, user_id=user_id,
            tenant_id=tenant_id, expires_at=NOW + timedelta(minutes=5),
            consumed_at=None,
        ))
        db.commit()

        class Forbidden:
            def __getattr__(self, name):
                raise AssertionError("Provider or verifier called before writer validation")

        with pytest.raises(ValueError, match="transactional SQLAlchemy repository"):
            claim_with_persistent_authorization(
                db=db, nonce_table=table,
                principal=AuthenticatedSaasPrincipal(
                    user_id=user_id, tenant_id=tenant_id,
                    account_active=True, email_verified=True, tenant_authorized=True,
                ),
                session_id=session_id, nonce=nonce, authorization_response={},
                verifier=Forbidden(), provider=Forbidden(), repository=Forbidden(),
                allowed_plans={}, expected_merchant_id="biz_test", now=NOW,
            )
        db.rollback()
        assert db.execute(select(table.c.consumed_at).where(table.c.nonce == nonce)).scalar_one() is None
    engine.dispose()
