"""Isolated reconciliation tests: synthetic provider and disposable SQLite."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.tenant import Tenant
from app.models.user import User
from app.models.whop_saas_subscription import WhopSaasSubscriptionBinding
from app.services.agency_saas_whop_guardrails import RecurringPlan, VerifiedSubscriptionFacts
from app.services.agency_saas_whop_repository import SQLAlchemyWhopSaasBindingRepository
from app.services.agency_saas_whop_reconciliation import reconcile_due_whop_saas_subscriptions

NOW = datetime.now(timezone.utc)
PLAN = RecurringPlan("prod_monthly_starter", "plan_monthly_starter", "starter", 1900)


@pytest.fixture()
def setup():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[
        Tenant.__table__, User.__table__, WhopSaasSubscriptionBinding.__table__,
    ])
    with Session(engine) as db:
        tenant = Tenant(name="Synthetic", slug="synthetic")
        db.add(tenant)
        db.flush()
        user = User(email="reconcile@example.com", password_hash="synthetic", tenant_id=tenant.id)
        db.add(user)
        db.flush()
        yield db, user
    engine.dispose()


def bind(db, user, suffix, observed_at=None):
    row = WhopSaasSubscriptionBinding(
        provider_subscription_id="sub_" + suffix,
        provider_customer_id="cus_" + suffix,
        tenant_id=user.tenant_id,
        user_id=user.id,
        provider_observed_at=observed_at,
    )
    db.add(row)
    db.commit()
    return row


class FakeProvider:
    def __init__(self):
        self.lookups = []
        self.fail_ids = set()
        self.statuses = {}

    def retrieve_verified_subscription(self, subscription_id):
        self.lookups.append(subscription_id)
        if subscription_id in self.fail_ids:
            raise RuntimeError("Provider temporary failure")
        suffix = subscription_id.removeprefix("sub_")
        return VerifiedSubscriptionFacts(
            merchant_id="biz_synthetic", product_id=PLAN.product_id,
            checkout_plan_id=PLAN.checkout_plan_id,
            subscription_id=subscription_id, customer_id="cus_" + suffix,
            provider_status=self.statuses.get(subscription_id, "active"),
            amount_usd_cents=1900, currency="USD", billing_interval="month",
            observed_at=NOW,
        )


def run(repo, provider, limit=100, cutoff=None):
    return reconcile_due_whop_saas_subscriptions(
        provider=provider, repository=repo, candidates=repo,
        expected_merchant_id="biz_synthetic",
        allowed_plans={PLAN.checkout_plan_id: PLAN},
        due_before=cutoff or NOW - timedelta(hours=8),
        limit=limit,
    )


def test_scan_only_due_bound_records_in_stable_order(setup):
    db, user = setup
    bind(db, user, "due", NOW - timedelta(hours=10))
    bind(db, user, "fresh", NOW - timedelta(hours=1))
    bind(db, user, "never")
    repo = SQLAlchemyWhopSaasBindingRepository(db)
    assert repo.list_due_subscription_ids(before=NOW - timedelta(hours=8), limit=100) == [
        "sub_never", "sub_due",
    ]
    provider = FakeProvider()
    result = run(repo, provider)
    assert result.examined == 2 and result.updated == 2 and result.failed == 0
    assert "sub_fresh" not in provider.lookups


def test_provider_failure_does_not_grant_and_other_accounts_continue(setup):
    db, user = setup
    bind(db, user, "a")
    bind(db, user, "b")
    provider = FakeProvider()
    provider.fail_ids.add("sub_a")
    repo = SQLAlchemyWhopSaasBindingRepository(db)
    result = run(repo, provider)
    assert result.examined == 2
    assert result.updated == 1 and result.failed == 1
    assert result.failed_subscription_ids == ("sub_a",)
    assert repo.get_decision("sub_a") is None
    assert repo.get_decision("sub_b").can_access is True


def test_cancellation_from_provider_revokes_prior_active_entitlement(setup):
    db, user = setup
    row = bind(db, user, "cancel")
    repo = SQLAlchemyWhopSaasBindingRepository(db)
    provider = FakeProvider()
    assert run(repo, provider).updated == 1
    provider.statuses["sub_cancel"] = "canceled"
    # The next provider snapshot is later than the persisted active one.
    # Simulate time passing by staling the DB record; the current snapshot
    # remains newer than that previous record.
    row.provider_observed_at = NOW - timedelta(hours=9)
    db.commit()
    result = run(repo, provider)
    assert result.updated == 1
    assert repo.get_decision("sub_cancel").can_access is False


def test_reconciliation_is_bounded_and_unconfigured_rejected(setup):
    db, user = setup
    bind(db, user, "a")
    bind(db, user, "b")
    repo = SQLAlchemyWhopSaasBindingRepository(db)
    provider = FakeProvider()
    assert run(repo, provider, limit=1).examined == 1
    with pytest.raises(ValueError, match="limit"):
        run(repo, provider, limit=101)
    with pytest.raises(ValueError, match="configuration"):
        reconcile_due_whop_saas_subscriptions(
            provider=provider, repository=repo, candidates=repo,
            expected_merchant_id="biz_synthetic", allowed_plans={},
            due_before=NOW,
        )


def test_missing_authorized_binding_cannot_grant(setup):
    db, user = setup
    bind(db, user, "a")
    repo = SQLAlchemyWhopSaasBindingRepository(db)

    class BogusCandidates:
        def list_due_subscription_ids(self, *, before, limit):
            return ["sub_unknown"]

    provider = FakeProvider()
    result = reconcile_due_whop_saas_subscriptions(
        provider=provider, repository=repo, candidates=BogusCandidates(),
        expected_merchant_id="biz_synthetic",
        allowed_plans={PLAN.checkout_plan_id: PLAN},
        due_before=NOW,
    )
    assert result.failed == 1
    assert not provider.lookups
    assert db.query(WhopSaasSubscriptionBinding).count() == 1


def test_reconciliation_rejects_cross_customer_snapshot_without_grant(setup):
    db, user = setup
    bind(db, user, "victim")
    repo = SQLAlchemyWhopSaasBindingRepository(db)

    class WrongCustomerProvider(FakeProvider):
        def retrieve_verified_subscription(self, subscription_id):
            facts = super().retrieve_verified_subscription(subscription_id)
            from dataclasses import replace
            return replace(facts, customer_id="cus_other_account")

    result = run(repo, WrongCustomerProvider())
    assert result.failed == 1 and result.updated == 0
    assert result.failed_subscription_ids == ("sub_victim",)
    assert repo.get_decision("sub_victim") is None


def test_reconciliation_rejects_mismatched_subscription_identity(setup):
    db, user = setup
    bind(db, user, "victim")
    repo = SQLAlchemyWhopSaasBindingRepository(db)

    class WrongSubscriptionProvider(FakeProvider):
        def retrieve_verified_subscription(self, subscription_id):
            facts = super().retrieve_verified_subscription(subscription_id)
            from dataclasses import replace
            return replace(facts, subscription_id="sub_other")

    result = run(repo, WrongSubscriptionProvider())
    assert result.failed == 1 and result.updated == 0
    assert repo.get_decision("sub_victim") is None


@pytest.mark.parametrize("override", [
    {"merchant_id": "biz_other"},
    {"product_id": "prod_other"},
    {"checkout_plan_id": "plan_other"},
    {"amount_usd_cents": 5900},
    {"currency": "EUR"},
    {"billing_interval": "year"},
])
def test_reconciliation_rejects_provider_plan_or_price_mismatch(setup, override):
    """A signed or authenticated lookup is not sufficient to grant wrong-tier access."""
    db, user = setup
    bind(db, user, "guarded")
    repo = SQLAlchemyWhopSaasBindingRepository(db)

    class MismatchedProvider(FakeProvider):
        def retrieve_verified_subscription(self, subscription_id):
            from dataclasses import replace
            return replace(super().retrieve_verified_subscription(subscription_id), **override)

    result = run(repo, MismatchedProvider())
    assert result.examined == 1 and result.failed == 1 and result.updated == 0
    assert repo.get_decision("sub_guarded") is None


def test_reconciliation_does_not_refresh_paid_access_on_provider_outage(setup):
    """A provider outage cannot move the last trusted observation forward."""
    db, user = setup
    bind(db, user, "outage")
    repo = SQLAlchemyWhopSaasBindingRepository(db)
    provider = FakeProvider()
    assert run(repo, provider).updated == 1
    original = repo.get_decision("sub_outage")
    row = db.query(WhopSaasSubscriptionBinding).filter_by(
        provider_subscription_id="sub_outage"
    ).one()
    original_observed_at = row.provider_observed_at
    provider.fail_ids.add("sub_outage")
    result = run(repo, provider, cutoff=NOW + timedelta(hours=1))
    assert result.failed == 1 and result.updated == 0
    db.refresh(row)
    assert row.provider_observed_at == original_observed_at
    assert repo.get_decision("sub_outage") == original



@pytest.mark.parametrize("terminal_status", ["canceled", "expired", "refunded"])
def test_reconciliation_never_reactivates_terminal_subscription(setup, terminal_status):
    """A later active snapshot cannot silently resurrect a terminal entitlement."""
    db, user = setup
    bind(db, user, "terminal")
    repo = SQLAlchemyWhopSaasBindingRepository(db)
    provider = FakeProvider()
    provider.statuses["sub_terminal"] = terminal_status
    class EarlierTerminalProvider(FakeProvider):
        def retrieve_verified_subscription(self, subscription_id):
            from dataclasses import replace
            return replace(super().retrieve_verified_subscription(subscription_id), observed_at=NOW - timedelta(seconds=2))
    terminal_provider = EarlierTerminalProvider()
    terminal_provider.statuses["sub_terminal"] = terminal_status
    assert run(repo, terminal_provider).updated == 1
    assert repo.get_decision("sub_terminal").can_access is False

    # Simulate a later provider observation, not a replay of the same snapshot.
    from dataclasses import replace
    class ReactivationProvider(FakeProvider):
        def retrieve_verified_subscription(self, subscription_id):
            return replace(
                super().retrieve_verified_subscription(subscription_id),
                observed_at=NOW,
            )

    # The validator must reject the terminal-to-active transition regardless
    # of timestamp; the provider client is not allowed to override it.
    result = run(repo, ReactivationProvider(), cutoff=NOW + timedelta(hours=1))
    assert result.failed == 1 and result.updated == 0
    assert repo.get_decision("sub_terminal").can_access is False


def test_reconciliation_rejects_conflicting_same_timestamp_state(setup):
    """An event with the same observation time cannot flip a persisted decision."""
    db, user = setup
    bind(db, user, "conflict")
    repo = SQLAlchemyWhopSaasBindingRepository(db)
    provider = FakeProvider()
    assert run(repo, provider).updated == 1
    provider.statuses["sub_conflict"] = "refunded"
    result = run(repo, provider, cutoff=NOW + timedelta(hours=1))
    assert result.failed == 1 and result.updated == 0
    assert repo.get_decision("sub_conflict").can_access is True
