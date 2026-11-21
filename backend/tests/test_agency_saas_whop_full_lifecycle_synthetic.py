"""Integrated synthetic checkout entitlement lifecycle; never calls Whop or charges.

Exercises the real SQLAlchemy persistence and workflow-plan lookups with
provider-authoritative fixtures: claim -> activation -> paid limits ->
cancellation -> free limits, with the legacy one-time Agency flow untouched.
This is NOT a real Whop payment acceptance test.
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.base import Base
from app.models.billing import Plan, Subscription
from app.models.tenant import Tenant
from app.models.user import User
from app.models.whop_saas_subscription import WhopSaasSubscriptionBinding
from app.services.agency_saas_whop_claim import (
    AuthenticatedSaasPrincipal, ProviderOwnershipProof, bind_verified_saas_subscription,
)
from app.services.agency_saas_whop_guardrails import (
    RecurringPlan, VerifiedSubscriptionFacts,
)
from app.services.agency_saas_whop_lifecycle import (
    AuthenticatedWebhookReference, process_verified_subscription_event,
)
from app.services.agency_saas_whop_repository import SQLAlchemyWhopSaasBindingRepository
from app.services.usage_limits import FREE_LIMITS, PLAN_LIMITS, get_active_plan_name, get_plan_limits


START = datetime.now(timezone.utc) - timedelta(minutes=5)
PLANS = (
    RecurringPlan("prod_saas_starter_ci", "plan_saas_starter_ci", "starter", 1900),
    RecurringPlan("prod_saas_pro_ci", "plan_saas_pro_ci", "pro", 5900),
    RecurringPlan("prod_saas_business_ci", "plan_saas_business_ci", "business", 14900),
)


class Provider:
    def __init__(self, facts):
        self.facts = facts
        self.reads = 0

    def retrieve_verified_subscription(self, subscription_id):
        self.reads += 1
        return self.facts


@pytest.fixture()
def environment(monkeypatch):
    monkeypatch.setattr(settings, "AGENCY_SAAS_WHOP_LIMITS_ENABLED", True)
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[
        Tenant.__table__, User.__table__, Plan.__table__,
        Subscription.__table__, WhopSaasSubscriptionBinding.__table__,
    ])
    with Session(engine) as db:
        tenant = Tenant(name="SaaS CI Customer", slug="saas-lifecycle-ci")
        db.add(tenant)
        db.flush()
        user = User(
            email="saas-lifecycle-ci@example.com",
            password_hash="synthetic-not-real",
            email_verified_at=START, tenant_id=tenant.id,
        )
        db.add(user)
        db.commit()
        yield db, user
    engine.dispose()


def verified_snapshot(plan, subscription_id, customer_id):
    return VerifiedSubscriptionFacts(
        merchant_id="biz_synthetic",
        product_id=plan.product_id, checkout_plan_id=plan.checkout_plan_id,
        subscription_id=subscription_id, customer_id=customer_id,
        provider_status="active", amount_usd_cents=plan.monthly_usd_cents,
        currency="USD", billing_interval="month", observed_at=START,
    )


def claim(db, user, plan):
    subscription_id = "sub_" + uuid4().hex
    customer_id = "cus_" + uuid4().hex
    facts = verified_snapshot(plan, subscription_id, customer_id)
    provider = Provider(facts)
    principal = AuthenticatedSaasPrincipal(
        user_id=str(user.id), tenant_id=str(user.tenant_id),
        account_active=True, email_verified=True, tenant_authorized=True,
    )
    proof = ProviderOwnershipProof(
        subscription_id=subscription_id, customer_id=customer_id,
        authorized_user_id=str(user.id),
        authorized_tenant_id=str(user.tenant_id),
        verified_by_provider=True, verified_for_session=True,
    )
    repository = SQLAlchemyWhopSaasBindingRepository(db)
    result = bind_verified_saas_subscription(
        principal=principal, proof=proof, provider=provider,
        repository=repository, expected_merchant_id="biz_synthetic",
        allowed_plans={plan.checkout_plan_id: plan},
    )
    assert result.newly_bound
    assert get_active_plan_name(db, user) == "free"
    return repository, provider, subscription_id


def update_from_provider(repository, provider, plan, subscription_id, event):
    return process_verified_subscription_event(
        event=AuthenticatedWebhookReference(
            event_id="evt_" + uuid4().hex, event_type=event,
            subscription_id=subscription_id,
        ),
        signature_verified=True, provider=provider, repository=repository,
        expected_merchant_id="biz_synthetic",
        allowed_plans={plan.checkout_plan_id: plan},
    )


@pytest.mark.parametrize("plan,expected_plan", [
    (PLANS[0], "starter"), (PLANS[1], "pro"), (PLANS[2], "enterprise"),
])
def test_full_synthetic_claim_activation_and_cancellation(environment, plan, expected_plan):
    db, user = environment
    repository, provider, sid = claim(db, user, plan)
    assert get_plan_limits(db, user) == FREE_LIMITS
    assert db.query(WhopSaasSubscriptionBinding).one().access_enabled is False

    activated = update_from_provider(
        repository, provider, plan, sid, "membership.activated",
    )
    assert activated.handled and activated.changed and activated.decision.can_access
    assert get_active_plan_name(db, user) == expected_plan
    assert get_plan_limits(db, user) == PLAN_LIMITS[expected_plan]

    # Replay of same authenticated event cannot create a second grant.
    duplicate = update_from_provider(
        repository, provider, plan, sid, "membership.activated",
    )
    assert duplicate.handled and not duplicate.changed

    from dataclasses import replace
    provider.facts = replace(
        provider.facts, provider_status="canceled",
        observed_at=START + timedelta(minutes=1),
    )
    canceled = update_from_provider(
        repository, provider, plan, sid, "membership.deactivated",
    )
    assert canceled.handled and canceled.changed
    assert not canceled.decision.can_access
    assert get_active_plan_name(db, user) == "free"
    assert get_plan_limits(db, user) == FREE_LIMITS
    assert db.query(WhopSaasSubscriptionBinding).count() == 1

    provider.facts = replace(
        provider.facts, provider_status="active",
        observed_at=START + timedelta(minutes=2),
    )
    with pytest.raises(ValueError, match="Terminal"):
        update_from_provider(
            repository, provider, plan, sid, "payment.succeeded",
        )
    assert get_plan_limits(db, user) == FREE_LIMITS


def test_forged_webhook_without_signature_never_grants(environment):
    db, user = environment
    plan = PLANS[0]
    repository, provider, sid = claim(db, user, plan)
    with pytest.raises(ValueError, match="signature"):
        process_verified_subscription_event(
            event=AuthenticatedWebhookReference(
                event_id="evt_fake", event_type="membership.activated",
                subscription_id=sid,
            ),
            signature_verified=False, provider=provider, repository=repository,
            expected_merchant_id="biz_synthetic",
            allowed_plans={plan.checkout_plan_id: plan},
        )
    assert get_plan_limits(db, user) == FREE_LIMITS


def test_refund_from_authoritative_provider_revokes(environment):
    db, user = environment
    plan = PLANS[1]
    repository, provider, sid = claim(db, user, plan)
    update_from_provider(repository, provider, plan, sid, "membership.activated")
    assert get_active_plan_name(db, user) == "pro"
    from dataclasses import replace
    provider.facts = replace(
        provider.facts, provider_status="refunded",
        observed_at=START + timedelta(minutes=1),
    )
    revoked = update_from_provider(repository, provider, plan, sid, "refund.updated")
    assert not revoked.decision.can_access
    assert get_plan_limits(db, user) == FREE_LIMITS
