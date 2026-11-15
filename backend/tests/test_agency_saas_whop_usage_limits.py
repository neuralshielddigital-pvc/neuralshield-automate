"""Default-off Whop tier enforcement integration tests; no external services."""
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.base import Base
from app.models.tenant import Tenant
from app.models.user import User
from app.models.whop_saas_subscription import WhopSaasSubscriptionBinding
from app.services.usage_limits import get_verified_whop_tier


@pytest.fixture
def whop_tier_db(monkeypatch):
    monkeypatch.setattr(settings, "AGENCY_SAAS_WHOP_LIMITS_ENABLED", True)
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine, tables=[Tenant.__table__, User.__table__, WhopSaasSubscriptionBinding.__table__]
    )
    with Session(engine) as db:
        tenant = Tenant(name="Isolated Tenant", slug="isolated-whop-tier")
        db.add(tenant)
        db.flush()
        user = User(email="tier@example.com", password_hash="synthetic", tenant_id=tenant.id)
        db.add(user)
        db.flush()
        yield db, user
    engine.dispose()


def add_subscription(db, user, tier="starter", state="active", enabled=True):
    row = WhopSaasSubscriptionBinding(
        provider_subscription_id="sub_ci_" + uuid4().hex,
        provider_customer_id="cus_ci_" + uuid4().hex,
        user_id=user.id, tenant_id=user.tenant_id,
        tier=tier, access_state=state, access_enabled=enabled,
        provider_observed_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    return row


@pytest.mark.parametrize("tier,expected", [
    ("starter", "starter"), ("pro", "pro"), ("business", "enterprise"),
])
def test_verified_whop_tiers_map_to_existing_limits(whop_tier_db, tier, expected):
    db, user = whop_tier_db
    add_subscription(db, user, tier=tier)
    assert get_verified_whop_tier(db, user) == expected


@pytest.mark.parametrize("state,enabled", [
    ("inactive", False), ("past_due", False), ("canceled", False),
    ("refunded", False), ("active", False),
])
def test_non_active_or_disabled_binding_never_grants(whop_tier_db, state, enabled):
    db, user = whop_tier_db
    add_subscription(db, user, state=state, enabled=enabled)
    assert get_verified_whop_tier(db, user) is None


def test_default_off_returns_none_even_with_active_binding(whop_tier_db, monkeypatch):
    db, user = whop_tier_db
    add_subscription(db, user)
    monkeypatch.setattr(settings, "AGENCY_SAAS_WHOP_LIMITS_ENABLED", False)
    assert get_verified_whop_tier(db, user) is None


def test_no_foreign_tenant_access(whop_tier_db):
    db, user = whop_tier_db
    add_subscription(db, user)
    other = SimpleNamespace(id=uuid4(), tenant_id=uuid4())
    assert get_verified_whop_tier(db, other) is None


def test_multiple_active_whop_subscriptions_fail_closed(whop_tier_db):
    db, user = whop_tier_db
    add_subscription(db, user)
    add_subscription(db, user, tier="pro")
    with pytest.raises(HTTPException) as error:
        get_verified_whop_tier(db, user)
    assert error.value.status_code == 409


def test_missing_verified_snapshot_cannot_grant(whop_tier_db):
    db, user = whop_tier_db
    row = add_subscription(db, user)
    row.provider_observed_at = None
    db.commit()
    assert get_verified_whop_tier(db, user) is None
