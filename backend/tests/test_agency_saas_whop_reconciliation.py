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


@pytest.mark.parametrize("candidate_ids", [
    ["sub_a", "sub_a"],  # duplicate could trigger repeated entitlement writes
    ["sub_a", ""],       # blank provider identity
    ["sub_a", None],     # malformed provider identity
    ["sub_a", ["sub_b"]],  # unhashable provider identity
    ["sub_a", "sub_b "],  # whitespace must not reach provider lookup
    ["sub_a", "sub_b/other"],  # path-like provider identity
    ["sub_a", "x" * 129],  # excessive provider identity length
    ["sub_a", "sub_b"],  # exceeds the requested single-record bound
])
def test_reconciliation_rejects_invalid_candidate_batch_before_provider_lookup(setup, candidate_ids):
    db, user = setup
    bind(db, user, "a")
    repo = SQLAlchemyWhopSaasBindingRepository(db)
    provider = FakeProvider()

    class InvalidCandidates:
        def list_due_subscription_ids(self, *, before, limit):
            return candidate_ids

    with pytest.raises(ValueError, match="Invalid or unbounded"):
        reconcile_due_whop_saas_subscriptions(
            provider=provider, repository=repo, candidates=InvalidCandidates(),
            expected_merchant_id="biz_synthetic",
            allowed_plans={PLAN.checkout_plan_id: PLAN},
            due_before=NOW, limit=1,
        )
    assert provider.lookups == []
    assert repo.get_decision("sub_a") is None


def test_reconciliation_rejects_naive_cutoff_before_any_lookup(setup):
    db, user = setup
    bind(db, user, "a")
    repo = SQLAlchemyWhopSaasBindingRepository(db)
    provider = FakeProvider()
    with pytest.raises(ValueError, match="timezone aware"):
        reconcile_due_whop_saas_subscriptions(
            provider=provider, repository=repo, candidates=repo,
            expected_merchant_id="biz_synthetic",
            allowed_plans={PLAN.checkout_plan_id: PLAN},
            due_before=datetime(2026, 11, 16),
        )
    assert provider.lookups == []


def test_reconciliation_calls_failure_alert_with_only_failed_ids(setup):
    db, user = setup
    bind(db, user, "alert")
    repo = SQLAlchemyWhopSaasBindingRepository(db)
    provider = FakeProvider()
    provider.fail_ids.add("sub_alert")
    alerts = []

    def alert_on_failure(*, failed_subscription_ids, examined):
        alerts.append((failed_subscription_ids, examined))

    report = reconcile_due_whop_saas_subscriptions(
        provider=provider, repository=repo, candidates=repo,
        expected_merchant_id="biz_synthetic",
        allowed_plans={PLAN.checkout_plan_id: PLAN},
        due_before=NOW, alert_on_failure=alert_on_failure,
    )
    assert report.failed == 1
    assert alerts == [(("sub_alert",), 1)]
    assert repo.get_decision("sub_alert") is None


def test_reconciliation_alert_delivery_failure_is_not_silent(setup):
    db, user = setup
    bind(db, user, "alert")
    repo = SQLAlchemyWhopSaasBindingRepository(db)
    provider = FakeProvider()
    provider.fail_ids.add("sub_alert")

    def failing_alert(*, failed_subscription_ids, examined):
        raise RuntimeError("Alert transport unavailable")

    with pytest.raises(RuntimeError, match="Alert transport unavailable"):
        reconcile_due_whop_saas_subscriptions(
            provider=provider, repository=repo, candidates=repo,
            expected_merchant_id="biz_synthetic",
            allowed_plans={PLAN.checkout_plan_id: PLAN},
            due_before=NOW, alert_on_failure=failing_alert,
        )
    assert repo.get_decision("sub_alert") is None



def test_strict_reconciliation_signals_partial_failure_after_alert(setup):
    """A scheduler must not mark a partially failed batch successful."""
    db, user = setup
    bind(db, user, "failed")
    bind(db, user, "healthy")
    repo = SQLAlchemyWhopSaasBindingRepository(db)
    provider = FakeProvider()
    provider.fail_ids.add("sub_failed")
    alerts = []

    def alert_on_failure(*, failed_subscription_ids, examined):
        alerts.append((failed_subscription_ids, examined))

    with pytest.raises(RuntimeError, match="failed for 1 subscriptions"):
        reconcile_due_whop_saas_subscriptions(
            provider=provider, repository=repo, candidates=repo,
            expected_merchant_id="biz_synthetic",
            allowed_plans={PLAN.checkout_plan_id: PLAN},
            due_before=NOW, alert_on_failure=alert_on_failure,
            raise_on_failure=True,
        )
    assert alerts == [(("sub_failed",), 2)]
    assert repo.get_decision("sub_failed") is None
    assert repo.get_decision("sub_healthy").can_access is True


def test_strict_reconciliation_succeeds_when_every_record_verified(setup):
    db, user = setup
    bind(db, user, "healthy")
    repo = SQLAlchemyWhopSaasBindingRepository(db)
    report = reconcile_due_whop_saas_subscriptions(
        provider=FakeProvider(), repository=repo, candidates=repo,
        expected_merchant_id="biz_synthetic",
        allowed_plans={PLAN.checkout_plan_id: PLAN},
        due_before=NOW, raise_on_failure=True,
    )
    assert report.failed == 0 and report.updated == 1


@pytest.mark.parametrize("bad_limit", [True, False, 0, 101, 1.5, "10", None])
def test_reconciliation_rejects_noninteger_or_out_of_range_limit_before_lookup(setup, bad_limit):
    db, user = setup
    bind(db, user, "a")
    repo = SQLAlchemyWhopSaasBindingRepository(db)
    provider = FakeProvider()
    with pytest.raises(ValueError, match="limit"):
        run(repo, provider, limit=bad_limit)
    assert provider.lookups == []


@pytest.mark.parametrize("bad_cutoff", [None, "2026-11-17", 42, datetime(2026, 11, 17)])
def test_reconciliation_rejects_invalid_cutoff_before_lookup(setup, bad_cutoff):
    db, user = setup
    bind(db, user, "a")
    repo = SQLAlchemyWhopSaasBindingRepository(db)
    provider = FakeProvider()
    with pytest.raises(ValueError, match="timezone aware"):
        reconcile_due_whop_saas_subscriptions(
            provider=provider, repository=repo, candidates=repo,
            expected_merchant_id="biz_synthetic",
            allowed_plans={PLAN.checkout_plan_id: PLAN},
            due_before=bad_cutoff,
        )
    assert provider.lookups == []


@pytest.mark.parametrize("bad_merchant", [None, 123, "", "other_merchant"])
def test_reconciliation_rejects_invalid_merchant_configuration_before_lookup(setup, bad_merchant):
    db, user = setup
    bind(db, user, "a")
    repo = SQLAlchemyWhopSaasBindingRepository(db)
    provider = FakeProvider()
    with pytest.raises(ValueError, match="configuration"):
        reconcile_due_whop_saas_subscriptions(
            provider=provider, repository=repo, candidates=repo,
            expected_merchant_id=bad_merchant,
            allowed_plans={PLAN.checkout_plan_id: PLAN},
            due_before=NOW,
        )
    assert provider.lookups == []



def test_reconciliation_caps_unbounded_candidate_iterator_before_lookup(setup):
    """A buggy scheduler source must not exhaust an unbounded generator."""
    db, user = setup
    bind(db, user, "a")
    repo = SQLAlchemyWhopSaasBindingRepository(db)
    provider = FakeProvider()
    yielded = []

    class UnboundedCandidates:
        def list_due_subscription_ids(self, *, before, limit):
            def generate():
                for index in range(1000000):
                    yielded.append(index)
                    if index > limit:
                        raise AssertionError("candidate iterator over-consumed")
                    yield "sub_" + str(index)
            return generate()

    with pytest.raises(ValueError, match="Invalid or unbounded"):
        reconcile_due_whop_saas_subscriptions(
            provider=provider, repository=repo, candidates=UnboundedCandidates(),
            expected_merchant_id="biz_synthetic",
            allowed_plans={PLAN.checkout_plan_id: PLAN},
            due_before=NOW, limit=2,
        )
    assert yielded == [0, 1, 2]
    assert provider.lookups == []
    assert repo.get_decision("sub_a") is None


def test_reconciliation_accepts_bounded_candidate_generator(setup):
    """A well-behaved lazy SQL candidate source remains supported."""
    db, user = setup
    bind(db, user, "a")
    repo = SQLAlchemyWhopSaasBindingRepository(db)

    class LazyCandidates:
        def list_due_subscription_ids(self, *, before, limit):
            yield "sub_a"

    report = reconcile_due_whop_saas_subscriptions(
        provider=FakeProvider(), repository=repo, candidates=LazyCandidates(),
        expected_merchant_id="biz_synthetic",
        allowed_plans={PLAN.checkout_plan_id: PLAN},
        due_before=NOW, limit=2,
    )
    assert report.examined == 1 and report.updated == 1 and report.failed == 0


@pytest.mark.parametrize("malformed_snapshot", [None, {}, [], "active", 123, object()])
def test_reconciliation_rejects_malformed_provider_snapshot_without_grant(setup, malformed_snapshot):
    """Malformed authenticated provider responses must not update paid entitlements."""
    db, user = setup
    bind(db, user, "malformed")
    repo = SQLAlchemyWhopSaasBindingRepository(db)

    class MalformedProvider:
        def retrieve_verified_subscription(self, subscription_id):
            assert subscription_id == "sub_malformed"
            return malformed_snapshot

    result = run(repo, MalformedProvider())
    assert result.examined == 1
    assert result.failed == 1 and result.updated == 0
    assert result.failed_subscription_ids == ("sub_malformed",)
    assert repo.get_decision("sub_malformed") is None


@pytest.mark.parametrize("invalid_plans", [
    None,
    [],
    "plan_monthly_starter",
    {"plan_monthly_starter": None},
    {"plan_monthly_starter": {"tier": "starter"}},
    {"wrong_plan": PLAN},
    {None: PLAN},
])
def test_reconciliation_rejects_invalid_plan_configuration_before_candidate_query(setup, invalid_plans):
    db, user = setup
    bind(db, user, "a")
    repo = SQLAlchemyWhopSaasBindingRepository(db)
    provider = FakeProvider()

    class NeverCandidates:
        def list_due_subscription_ids(self, *, before, limit):
            raise AssertionError("invalid config reached candidate query")

    with pytest.raises(ValueError, match="configuration"):
        reconcile_due_whop_saas_subscriptions(
            provider=provider, repository=repo, candidates=NeverCandidates(),
            expected_merchant_id="biz_synthetic", allowed_plans=invalid_plans,
            due_before=NOW,
        )
    assert provider.lookups == []
    assert repo.get_decision("sub_a") is None


@pytest.mark.parametrize("invalid_merchant", [
    "biz_", "biz_merchant extra", "biz_merchant\\n", "biz_" + "x" * 129,
])
def test_reconciliation_rejects_malformed_merchant_before_candidate_query(setup, invalid_merchant):
    db, user = setup
    bind(db, user, "a")
    repo = SQLAlchemyWhopSaasBindingRepository(db)

    class NeverCandidates:
        def list_due_subscription_ids(self, *, before, limit):
            raise AssertionError("invalid config reached candidate query")

    with pytest.raises(ValueError, match="configuration"):
        reconcile_due_whop_saas_subscriptions(
            provider=FakeProvider(), repository=repo, candidates=NeverCandidates(),
            expected_merchant_id=invalid_merchant,
            allowed_plans={PLAN.checkout_plan_id: PLAN}, due_before=NOW,
        )


@pytest.mark.parametrize("field,bad_value", [
    ("tenant_id", None),
    ("tenant_id", 123),
    ("user_id", []),
    ("provider_customer_id", 42),
])
def test_reconciliation_fails_closed_on_malformed_binding_identity(setup, field, bad_value):
    """Corrupted repository identities must never reach the provider or grant access."""
    from dataclasses import replace

    db, user = setup
    bind(db, user, "malformed")
    real_repo = SQLAlchemyWhopSaasBindingRepository(db)

    class CorruptRepository:
        def get_binding(self, subscription_id):
            return replace(real_repo.get_binding(subscription_id), **{field: bad_value})

    class DueCandidates:
        def list_due_subscription_ids(self, *, before, limit):
            return ["sub_malformed"]

    provider = FakeProvider()
    result = reconcile_due_whop_saas_subscriptions(
        provider=provider, repository=CorruptRepository(), candidates=DueCandidates(),
        expected_merchant_id="biz_synthetic",
        allowed_plans={PLAN.checkout_plan_id: PLAN}, due_before=NOW,
    )
    assert result.failed_subscription_ids == ("sub_malformed",)
    assert result.updated == 0
    assert provider.lookups == []
    assert real_repo.get_decision("sub_malformed") is None
