"""First-claim authorization and persistence tests, synthetic accounts only."""
from dataclasses import replace
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.tenant import Tenant
from app.models.user import User
from app.models.whop_saas_subscription import WhopSaasSubscriptionBinding
from app.services.agency_saas_whop_claim import (
    AuthenticatedSaasPrincipal, ProviderOwnershipProof,
    bind_verified_saas_subscription,
)
from app.services.agency_saas_whop_guardrails import (
    RecurringPlan, VerifiedSubscriptionFacts,
)
from app.services.agency_saas_whop_repository import SQLAlchemyWhopSaasBindingRepository

PLAN = RecurringPlan("prod_saas_starter", "plan_saas_starter", "starter", 1900)


class FakeProvider:
    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.lookups = []

    def retrieve_verified_subscription(self, subscription_id):
        self.lookups.append(subscription_id)
        return self.snapshot


@pytest.fixture
def claim_env():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[
        Tenant.__table__, User.__table__, WhopSaasSubscriptionBinding.__table__,
    ])
    with Session(engine) as db:
        tenant = Tenant(name="Claim Test", slug="claim-test")
        db.add(tenant)
        db.flush()
        user = User(email="claim@example.com", password_hash="synthetic", tenant_id=tenant.id)
        db.add(user)
        db.commit()
        principal = AuthenticatedSaasPrincipal(
            user_id=str(user.id), tenant_id=str(tenant.id),
            account_active=True, email_verified=True, tenant_authorized=True,
        )
        proof = ProviderOwnershipProof(
            subscription_id="sub_synthetic_claim",
            customer_id="cus_synthetic_claim",
            authorized_user_id=principal.user_id,
            authorized_tenant_id=principal.tenant_id,
            verified_by_provider=True,
            verified_for_session=True,
        )
        snapshot = VerifiedSubscriptionFacts(
            merchant_id="biz_synthetic",
            product_id=PLAN.product_id, checkout_plan_id=PLAN.checkout_plan_id,
            subscription_id=proof.subscription_id, customer_id=proof.customer_id,
            provider_status="active", amount_usd_cents=1900, currency="USD",
            billing_interval="month", observed_at=datetime.now(timezone.utc),
        )
        yield db, principal, proof, FakeProvider(snapshot)
    engine.dispose()


def claim(db, principal, proof, provider, **overrides):
    args = dict(
        principal=principal, proof=proof, provider=provider,
        repository=SQLAlchemyWhopSaasBindingRepository(db),
        expected_merchant_id="biz_synthetic",
        allowed_plans={PLAN.checkout_plan_id: PLAN},
    )
    args.update(overrides)
    return bind_verified_saas_subscription(**args)


def test_claim_creates_only_inactive_disabled_binding(claim_env):
    db, principal, proof, provider = claim_env
    outcome = claim(db, principal, proof, provider)
    assert outcome.newly_bound and outcome.subscription_id == proof.subscription_id
    row = db.query(WhopSaasSubscriptionBinding).one()
    assert row.tenant_id == principal.tenant_id or str(row.tenant_id) == principal.tenant_id
    assert not row.access_enabled
    assert row.access_state == "inactive"
    assert row.tier == "unverified"
    assert row.provider_observed_at is None
    assert provider.lookups == [proof.subscription_id]


def test_same_owner_claim_is_idempotent_without_grant(claim_env):
    db, principal, proof, provider = claim_env
    assert claim(db, principal, proof, provider).newly_bound
    assert not claim(db, principal, proof, provider).newly_bound
    assert db.query(WhopSaasSubscriptionBinding).count() == 1
    assert not db.query(WhopSaasSubscriptionBinding).one().access_enabled


@pytest.mark.parametrize("changes", [
    {"account_active": False},
    {"email_verified": False},
    {"tenant_authorized": False},
    {"user_id": ""},
])
def test_unauthorized_principal_rejected_before_provider_lookup(claim_env, changes):
    db, principal, proof, provider = claim_env
    with pytest.raises(ValueError, match="principal"):
        claim(db, replace(principal, **changes), proof, provider)
    assert not provider.lookups
    assert db.query(WhopSaasSubscriptionBinding).count() == 0


@pytest.mark.parametrize("changes", [
    {"verified_by_provider": False},
    {"verified_for_session": False},
    {"authorized_user_id": str(uuid4())},
    {"authorized_tenant_id": str(uuid4())},
    {"customer_id": ""},
    {"subscription_id": ""},
])
def test_missing_or_foreign_ownership_proof_rejected(claim_env, changes):
    db, principal, proof, provider = claim_env
    with pytest.raises(ValueError, match="ownership"):
        claim(db, principal, replace(proof, **changes), provider)
    assert not provider.lookups
    assert db.query(WhopSaasSubscriptionBinding).count() == 0


@pytest.mark.parametrize("changes", [
    {"subscription_id": "sub_different"},
    {"customer_id": "cus_different"},
    {"product_id": "prod_onetime"},
    {"checkout_plan_id": "plan_unknown"},
    {"merchant_id": "biz_wrong"},
    {"amount_usd_cents": 2700},
    {"currency": "EUR"},
    {"billing_interval": "year"},
])
def test_bad_independent_provider_contract_prevents_binding(claim_env, changes):
    db, principal, proof, provider = claim_env
    provider.snapshot = replace(provider.snapshot, **changes)
    with pytest.raises(ValueError):
        claim(db, principal, proof, provider)
    assert db.query(WhopSaasSubscriptionBinding).count() == 0


def test_other_principal_cannot_take_over_existing_binding(claim_env):
    db, principal, proof, provider = claim_env
    claim(db, principal, proof, provider)
    attacker = replace(principal, user_id=str(uuid4()), tenant_id=str(uuid4()))
    spoofed_proof = replace(
        proof, authorized_user_id=attacker.user_id,
        authorized_tenant_id=attacker.tenant_id,
    )
    with pytest.raises(ValueError, match="different SaaS account"):
        claim(db, attacker, spoofed_proof, provider)
    row = db.query(WhopSaasSubscriptionBinding).one()
    assert str(row.user_id) == principal.user_id
    assert not row.access_enabled


@pytest.mark.parametrize("changes", [
    {"account_active": 1},
    {"email_verified": "true"},
    {"tenant_authorized": 1},
    {"user_id": None},
    {"tenant_id": 123},
])
def test_claim_rejects_noncanonical_principal_fields_before_lookup(claim_env, changes):
    db, principal, proof, provider = claim_env
    with pytest.raises(ValueError, match="principal"):
        claim(db, replace(principal, **changes), proof, provider)
    assert provider.lookups == []
    assert db.query(WhopSaasSubscriptionBinding).count() == 0


@pytest.mark.parametrize("changes", [
    {"verified_by_provider": 1},
    {"verified_for_session": "true"},
    {"subscription_id": None},
    {"customer_id": 123},
    {"authorized_user_id": None},
    {"authorized_tenant_id": 123},
])
def test_claim_rejects_noncanonical_ownership_proof_before_lookup(claim_env, changes):
    db, principal, proof, provider = claim_env
    with pytest.raises(ValueError, match="ownership"):
        claim(db, principal, replace(proof, **changes), provider)
    assert provider.lookups == []
    assert db.query(WhopSaasSubscriptionBinding).count() == 0


@pytest.mark.parametrize("field,bad_value", [
    ("user_id", " leading"),
    ("tenant_id", "trailing "),
    ("user_id", "control\nchar"),
    ("tenant_id", "x" * 129),
    ("user_id", "unicode_é"),
])
def test_claim_rejects_ambiguous_principal_identity_before_lookup(claim_env, field, bad_value):
    db, principal, proof, provider = claim_env
    with pytest.raises(ValueError, match="principal"):
        claim(db, replace(principal, **{field: bad_value}), proof, provider)
    assert provider.lookups == []
    assert db.query(WhopSaasSubscriptionBinding).count() == 0


@pytest.mark.parametrize("field,bad_value", [
    ("subscription_id", "sub_unsafe\n"),
    ("customer_id", " cus_unsafe"),
    ("authorized_user_id", "x" * 129),
    ("authorized_tenant_id", "unicode_é"),
])
def test_claim_rejects_ambiguous_proof_identity_before_lookup(claim_env, field, bad_value):
    db, principal, proof, provider = claim_env
    with pytest.raises(ValueError, match="ownership"):
        claim(db, principal, replace(proof, **{field: bad_value}), provider)
    assert provider.lookups == []
    assert db.query(WhopSaasSubscriptionBinding).count() == 0


@pytest.mark.parametrize("invalid_snapshot", [None, {}, [], "active", 123, object()])
def test_claim_rejects_malformed_provider_snapshot_without_binding(claim_env, invalid_snapshot):
    db, principal, proof, provider = claim_env
    provider.snapshot = invalid_snapshot
    with pytest.raises(ValueError, match="invalid verified subscription snapshot"):
        claim(db, principal, proof, provider)
    assert provider.lookups == [proof.subscription_id]
    assert db.query(WhopSaasSubscriptionBinding).count() == 0


@pytest.mark.parametrize("invalid_principal", [None, {}, [], "user", object()])
def test_claim_rejects_untyped_principal_before_provider_lookup(claim_env, invalid_principal):
    db, _principal, proof, provider = claim_env
    with pytest.raises(ValueError, match="principal"):
        claim(db, invalid_principal, proof, provider)
    assert provider.lookups == []
    assert db.query(WhopSaasSubscriptionBinding).count() == 0


@pytest.mark.parametrize("invalid_proof", [None, {}, [], "verified", object()])
def test_claim_rejects_untyped_proof_before_provider_lookup(claim_env, invalid_proof):
    db, principal, _proof, provider = claim_env
    with pytest.raises(ValueError, match="ownership"):
        claim(db, principal, invalid_proof, provider)
    assert provider.lookups == []
    assert db.query(WhopSaasSubscriptionBinding).count() == 0


@pytest.mark.parametrize("provider_error", [
    TimeoutError("synthetic provider timeout"),
    ConnectionError("synthetic provider unavailable"),
    RuntimeError("synthetic upstream failure"),
])
def test_claim_provider_failure_never_creates_binding(claim_env, provider_error):
    db, principal, proof, provider = claim_env

    def fail_lookup(subscription_id):
        provider.lookups.append(subscription_id)
        raise provider_error

    provider.retrieve_verified_subscription = fail_lookup
    with pytest.raises(type(provider_error)):
        claim(db, principal, proof, provider)
    assert provider.lookups == [proof.subscription_id]
    assert db.query(WhopSaasSubscriptionBinding).count() == 0


@pytest.mark.parametrize("field,bad_value", [
    ("user_id", "not-a-uuid"),
    ("tenant_id", "12345678-1234-1234-1234-123456789ABC"),
    ("user_id", "12345678123412341234123456789abc"),
])
def test_claim_rejects_noncanonical_principal_uuid_before_provider_lookup(claim_env, field, bad_value):
    db, principal, proof, provider = claim_env
    with pytest.raises(ValueError, match="principal"):
        claim(db, replace(principal, **{field: bad_value}), proof, provider)
    assert provider.lookups == []
    assert db.query(WhopSaasSubscriptionBinding).count() == 0


@pytest.mark.parametrize("field,bad_value", [
    ("authorized_user_id", "not-a-uuid"),
    ("authorized_tenant_id", "12345678-1234-1234-1234-123456789ABC"),
    ("authorized_user_id", "12345678123412341234123456789abc"),
])
def test_claim_rejects_noncanonical_proof_uuid_before_provider_lookup(claim_env, field, bad_value):
    db, principal, proof, provider = claim_env
    with pytest.raises(ValueError, match="ownership"):
        claim(db, principal, replace(proof, **{field: bad_value}), provider)
    assert provider.lookups == []
    assert db.query(WhopSaasSubscriptionBinding).count() == 0
