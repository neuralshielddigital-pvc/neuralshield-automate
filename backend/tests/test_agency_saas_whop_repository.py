"""Repository-only synthetic tests for durable Whop SaaS access state.

SQLite tests verify transaction behavior; production PostgreSQL migration
and locking still require a dedicated integration test before deployment.
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.tenant import Tenant
from app.models.user import User
from app.models.whop_saas_subscription import WhopSaasSubscriptionBinding
from app.services.agency_saas_whop_guardrails import (
    EntitlementState, SubscriptionDecision,
)
from app.services.agency_saas_whop_repository import SQLAlchemyWhopSaasBindingRepository


STAMP = datetime(2026, 11, 15, tzinfo=timezone.utc)


@pytest.fixture()
def bound_db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[
        Tenant.__table__, User.__table__,
        WhopSaasSubscriptionBinding.__table__,
    ])
    with Session(engine) as db:
        tenant = Tenant(name="Synthetic Agency", slug="synthetic-agency")
        db.add(tenant)
        db.flush()
        user = User(
            email="synthetic@example.com", password_hash="not-a-real-password-hash",
            tenant_id=tenant.id,
        )
        db.add(user)
        db.flush()
        binding = WhopSaasSubscriptionBinding(
            provider_subscription_id="sub_synthetic",
            provider_customer_id="cus_synthetic",
            tenant_id=tenant.id,
            user_id=user.id,
        )
        db.add(binding)
        db.commit()
        yield db
    engine.dispose()


def decision(status=EntitlementState.ACTIVE, at=STAMP):
    return SubscriptionDecision(
        "sub_synthetic", "starter", status,
        status is EntitlementState.ACTIVE, at,
    )


def test_new_binding_starts_without_access(bound_db):
    repository = SQLAlchemyWhopSaasBindingRepository(bound_db)
    assert repository.get_decision("sub_synthetic") is None
    binding = repository.get_binding("sub_synthetic")
    assert binding.provider_customer_id == "cus_synthetic"
    row = bound_db.query(WhopSaasSubscriptionBinding).one()
    assert row.access_enabled is False


def test_active_then_canceled_is_durable_and_idempotent(bound_db):
    repository = SQLAlchemyWhopSaasBindingRepository(bound_db)
    binding = repository.get_binding("sub_synthetic")
    assert repository.apply_if_current(binding, decision()) is True
    assert repository.get_decision("sub_synthetic").can_access is True
    assert repository.apply_if_current(binding, decision()) is False
    canceled = decision(EntitlementState.CANCELED, STAMP + timedelta(minutes=1))
    assert repository.apply_if_current(binding, canceled) is True
    current = repository.get_decision("sub_synthetic")
    assert current.state is EntitlementState.CANCELED
    assert current.can_access is False
    assert repository.apply_if_current(binding, canceled) is False


def test_stale_event_cannot_reactivate_canceled_access(bound_db):
    repository = SQLAlchemyWhopSaasBindingRepository(bound_db)
    binding = repository.get_binding("sub_synthetic")
    repository.apply_if_current(binding, decision(
        EntitlementState.CANCELED, STAMP + timedelta(hours=1)
    ))
    with pytest.raises(ValueError):
        repository.apply_if_current(binding, decision())
    assert not repository.get_decision("sub_synthetic").can_access


def test_newer_event_cannot_reactivate_terminal_subscription(bound_db):
    repository = SQLAlchemyWhopSaasBindingRepository(bound_db)
    binding = repository.get_binding("sub_synthetic")
    repository.apply_if_current(binding, decision(EntitlementState.REFUNDED))
    with pytest.raises(ValueError, match="Terminal"):
        repository.apply_if_current(
            binding, decision(at=STAMP + timedelta(minutes=3))
        )


def test_customer_rebinding_rejected(bound_db):
    repository = SQLAlchemyWhopSaasBindingRepository(bound_db)
    binding = repository.get_binding("sub_synthetic")
    changed = type(binding)(
        subscription_id=binding.subscription_id,
        provider_customer_id="cus_attacker",
        tenant_id=binding.tenant_id,
        user_id=binding.user_id,
    )
    with pytest.raises(ValueError, match="binding changed"):
        repository.apply_if_current(changed, decision())
    assert repository.get_decision("sub_synthetic") is None


def test_absent_binding_never_created_from_webhook(bound_db):
    repository = SQLAlchemyWhopSaasBindingRepository(bound_db)
    binding = repository.get_binding("sub_synthetic")
    unknown = type(binding)(
        subscription_id="sub_unknown",
        provider_customer_id=binding.provider_customer_id,
        tenant_id=binding.tenant_id,
        user_id=binding.user_id,
    )
    with pytest.raises(ValueError, match="No authorized"):
        repository.apply_if_current(
            unknown,
            SubscriptionDecision("sub_unknown", "starter", EntitlementState.ACTIVE, True, STAMP),
        )
    assert bound_db.query(WhopSaasSubscriptionBinding).count() == 1


def test_inconsistent_grant_rejected(bound_db):
    repository = SQLAlchemyWhopSaasBindingRepository(bound_db)
    binding = repository.get_binding("sub_synthetic")
    invalid = SubscriptionDecision(
        "sub_synthetic", "starter", EntitlementState.EXPIRED, True, STAMP
    )
    with pytest.raises(ValueError, match="Inconsistent"):
        repository.apply_if_current(binding, invalid)
    assert repository.get_decision("sub_synthetic") is None


def test_same_timestamp_conflicting_tier_rejected(bound_db):
    repository = SQLAlchemyWhopSaasBindingRepository(bound_db)
    binding = repository.get_binding("sub_synthetic")
    repository.apply_if_current(binding, decision())
    with pytest.raises(ValueError, match="Conflicting"):
        repository.apply_if_current(
            binding,
            SubscriptionDecision("sub_synthetic", "pro", EntitlementState.ACTIVE, True, STAMP),
        )


def test_altered_existing_binding_detected(bound_db):
    repository = SQLAlchemyWhopSaasBindingRepository(bound_db)
    binding = repository.get_binding("sub_synthetic")
    with pytest.raises(ValueError):
        repository.apply_if_current(
            type(binding)(
                subscription_id=binding.subscription_id,
                provider_customer_id=binding.provider_customer_id,
                tenant_id=str(uuid4()), user_id=binding.user_id,
            ),
            decision(),
        )


def test_idempotent_replay_releases_database_transaction(bound_db):
    """A duplicate signed delivery must not retain a PostgreSQL row lock."""
    repository = SQLAlchemyWhopSaasBindingRepository(bound_db)
    binding = repository.get_binding("sub_synthetic")
    assert repository.apply_if_current(binding, decision()) is True
    assert repository.apply_if_current(binding, decision()) is False
    assert not bound_db.in_transaction()
    assert repository.get_decision("sub_synthetic").can_access is True
