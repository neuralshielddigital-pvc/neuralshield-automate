"""Durable ownership, replay, lifecycle and legacy isolation with real ORM writes."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import importlib.util
import json
import os
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session
from alembic.migration import MigrationContext
from alembic.operations import Operations

from app.core.config import settings
from app.models.base import Base
from app.models.tenant import Tenant
from app.models.user import User
from app.models.billing import Plan, Subscription, Payment
from app.models.enums import PlanInterval, SubscriptionStatus
from app.models.automation_whop import AutomationWhopIntent as Intent, AutomationWhopMembership as Member, AutomationWhopPayment as Receipt, AutomationWhopEvent
from app.services.automation_whop_catalog import VERSION
from app.services.automation_whop_service import AutomationWhopService, effective_membership
from app.services.automation_whop_transport import WhopAdapter, WhopSettings, WhopError, WhopUnavailable
from app.services.usage_limits import get_plan_limits, FREE_LIMITS
from test_automation_whop_paid_period import period_resources

NOW = datetime(2026, 11, 15, 12, tzinfo=timezone.utc)
TABLES = [Tenant.__table__, User.__table__, Plan.__table__, Subscription.__table__, Payment.__table__, Intent.__table__, Member.__table__, Receipt.__table__, AutomationWhopEvent.__table__]


@pytest.fixture
def db():
    url = os.environ.get("AGENCY_WHOP_TEST_DATABASE_URL", "")
    if url:
        if not url.startswith("postgresql") or "127.0.0.1:55432/" not in url:
            pytest.fail("Only disposable CI PostgreSQL is permitted")
        schema = "auto_test_" + uuid4().hex
        parent = create_engine(url)
        with parent.begin() as connection:
            connection.execute(text('CREATE SCHEMA "' + schema + '"'))
        engine = create_engine(url, connect_args={"options": "-csearch_path=" + schema})
    else:
        engine = create_engine("sqlite://")
    Base.metadata.create_all(engine, tables=TABLES)
    with Session(engine, expire_on_commit=False) as session:
        tenant = Tenant(name="Synthetic", slug="synthetic")
        session.add(tenant); session.flush()
        user = User(email="synthetic@example.test", password_hash="unused", tenant_id=tenant.id,
                    email_verified_at=NOW, is_active=True)
        session.add(user)
        session.add_all([Plan(name="Starter", price=Decimal(19), interval=PlanInterval.monthly, stripe_price_id="synthetic-starter"),
                         Plan(name="Pro", price=Decimal(149), interval=PlanInterval.monthly, stripe_price_id="legacy-pro-149"),
                         Plan(name="Pro", price=Decimal(59), interval=PlanInterval.monthly, stripe_price_id="synthetic-pro")])
        session.commit()
        yield session, user
    engine.dispose()
    if url:
        with parent.begin() as connection:
            connection.execute(text('DROP SCHEMA "' + schema + '" CASCADE'))
        parent.dispose()


@pytest.fixture
def setup(db, monkeypatch):
    session, user = db
    for key, value in {"AUTOMATION_WHOP_ENABLED": True,
                       "AUTOMATION_WHOP_STARTER_PRODUCT_ID": "prod_test",
                       "AUTOMATION_WHOP_STARTER_PLAN_ID": "plan_test"}.items():
        monkeypatch.setattr(settings, key, value)
    for code in ("PRO", "BUSINESS"):
        monkeypatch.setattr(settings, "AUTOMATION_WHOP_" + code + "_PRODUCT_ID", "prod_other" + code)
        monkeypatch.setattr(settings, "AUTOMATION_WHOP_" + code + "_PLAN_ID", "plan_other" + code)
    data = period_resources()
    price = {"currency": "usd", "amount": "19.00"}
    payment = data["/api/v1/payments/pay_test"]
    payment.update(subtotal=price, total=price)
    payment["line_items"][0]["subtotal"] = price
    data["/api/v1/variants/plan_test"]["renewal_price"] = 19
    calls = []
    def respond(request):
        calls.append(request)
        if request.method == "POST":
            payload = json.loads(request.content)
            return httpx.Response(200, json={"id": "ch_test", "account_id": "biz_test", "mode": "payment",
                "metadata": payload["metadata"], "variant": {"id": "plan_test"},
                "purchase_url": "https://whop.com/checkout/ch_test"})
        if request.url.path == "/api/v1/payments":
            return httpx.Response(200, json={"data": [{"id": "pay_test"}], "page_info": {"has_next_page": False}})
        return httpx.Response(200, json=data[request.url.path])
    provider = WhopAdapter(WhopSettings("biz_test", "synthetic-key", environment="production", enabled=True),
                           httpx.Client(transport=httpx.MockTransport(respond)))
    service = AutomationWhopService(session, provider)
    return session, user, data, service, calls


def start(setup):
    session, user, data, service, calls = setup
    result = service.checkout(user, "starter", uuid4())
    row = session.scalar(select(Intent))
    metadata = {"nsauto_intent_id": str(row.id), "nsauto_tenant_id": str(user.tenant_id), "nsauto_catalog_version": VERSION}
    data["/api/v1/payments/pay_test"]["metadata"] = metadata
    data["/api/v1/memberships/mem_test"]["metadata"] = metadata
    return row, result


def test_checkout_reuses_command_and_other_tabs_without_second_provider_write(setup):
    session, user, data, service, calls = setup
    row, first = start(setup)
    assert service.checkout(user, "starter", uuid4()) == first
    assert len([r for r in calls if r.method == "POST"]) == 1
    assert calls[-1].headers["idempotency-key"] == "nsauto-checkout-" + str(row.id)
    assert session.scalar(select(Member)) is None
    with pytest.raises(HTTPException, match="") as error:
        service.checkout(user, "pro", uuid4())
    assert error.value.status_code == 409


def test_unverified_email_cannot_create_checkout(setup):
    session, user, data, service, calls = setup
    user.email_verified_at = None
    with pytest.raises(HTTPException) as error:
        service.checkout(user, "starter", uuid4())
    assert error.value.status_code == 403 and not calls
    assert session.scalar(select(Intent)) is None


def test_paid_period_projection_and_refund_are_idempotent_and_terminal(setup):
    session, user, data, service, calls = setup
    start(setup)
    assert service.reconcile_payment("pay_test", NOW)
    session.commit()
    assert service.reconcile_payment("pay_test", NOW)
    session.commit()
    assert len(session.scalars(select(Subscription)).all()) == 1
    assert len(session.scalars(select(Payment)).all()) == 1
    assert effective_membership(session, user, NOW).cancel_at_period_end
    data["/api/v1/payments/pay_test"]["refunded_amount"] = {"currency": "usd", "amount": "1.00"}
    assert not service.reconcile_payment("pay_test", NOW)
    session.commit()
    data["/api/v1/payments/pay_test"].pop("refunded_amount")
    assert not service.reconcile_payment("pay_test", NOW)
    session.commit()
    assert effective_membership(session, user, NOW) is None
    assert session.scalar(select(Subscription)).status == SubscriptionStatus.CANCELED


def test_stale_and_expired_evidence_cannot_grant_from_legacy_projection(setup, monkeypatch):
    session, user, data, service, calls = setup
    start(setup); service.reconcile_payment("pay_test", NOW); session.commit()
    assert effective_membership(session, user, NOW + timedelta(minutes=11)) is None
    assert effective_membership(session, user, NOW + timedelta(days=31)) is None
    assert get_plan_limits(session, user) == FREE_LIMITS  # fixture period is in the past at runtime


def test_wrong_tenant_metadata_and_unknown_intent_never_create_member(setup):
    session, user, data, service, calls = setup
    start(setup)
    data["/api/v1/payments/pay_test"]["metadata"]["nsauto_tenant_id"] = str(uuid4())
    with pytest.raises(WhopError):
        service.reconcile_payment("pay_test", NOW)
    session.rollback()
    assert session.scalar(select(Member)) is None
    assert session.scalar(select(Payment)) is None


def test_new_owner_cannot_rebind_existing_provider_membership(setup):
    session, user, data, service, calls = setup
    row, _ = start(setup); service.reconcile_payment("pay_test", NOW); session.commit()
    second = User(email="other@example.test", password_hash="unused", tenant_id=user.tenant_id, email_verified_at=NOW)
    session.add(second); session.flush()
    other = Intent(id=uuid4(), user_id=second.id, tenant_id=second.tenant_id, command_id=str(uuid4()),
        plan_code="starter", catalog_version=VERSION, amount_minor=1900, configuration_id="ch_other")
    session.add(other); session.commit()
    metadata = service.provider._metadata(__import__('app.services.automation_whop_service',fromlist=['contract']).contract(other))
    data["/api/v1/payments/pay_test"]["metadata"] = metadata
    data["/api/v1/memberships/mem_test"]["metadata"] = metadata
    with pytest.raises(WhopError, match="membership_already_owned"):
        service.reconcile_payment("pay_test", NOW)
    session.rollback()
    assert session.get(Member,"mem_test").user_id == user.id


def test_expired_or_unpaid_renewal_does_not_extend_access(setup):
    session, user, data, service, calls = setup
    start(setup); service.reconcile_payment("pay_test", NOW); session.commit()
    member = data["/api/v1/memberships/mem_test"]
    member.update(current_period_start="2026-12-14T12:00:00Z",current_period_end="2027-01-13T12:00:00Z")
    service.refresh_membership("mem_test", NOW + timedelta(days=30))
    session.commit()
    assert not session.get(Member,"mem_test").active
    assert effective_membership(session,user,NOW+timedelta(days=30)) is None


def test_legacy_active_subscription_is_preserved_and_blocks_duplicate_checkout(setup):
    session, user, data, service, calls = setup
    plan = session.scalar(select(Plan).where(Plan.name == "Starter"))
    sub = Subscription(user_id=user.id,tenant_id=user.tenant_id,stripe_customer_id="legacy",stripe_subscription_id="legacy-unchanged",plan_id=plan.id,status=SubscriptionStatus.ACTIVE)
    session.add(sub); session.commit()
    with pytest.raises(HTTPException) as error:
        service.checkout(user,"starter",uuid4())
    assert error.value.status_code == 409 and not calls
    assert session.get(Subscription,sub.id).status == SubscriptionStatus.ACTIVE


def test_migration_is_additive_and_refuses_to_destroy_checkout_records(db):
    session, user = db
    session.commit()
    engine = session.get_bind()
    whop_tables = [AutomationWhopEvent.__table__, Receipt.__table__, Member.__table__, Intent.__table__]
    with engine.begin() as connection:
        # metadata.drop_all also emits unrelated shared Enum DROP statements.
        # Drop only these empty synthetic checkout tables in this test schema.
        from sqlalchemy.schema import DropTable
        for table in whop_tables:
            connection.execute(DropTable(table))
        path = Path(__file__).resolve().parents[1] / "alembic/versions/20261124_0003_automation_whop_checkout.py"
        spec = importlib.util.spec_from_file_location("auto_whop_migration", path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
        from sqlalchemy import inspect
        for table in whop_tables:
            columns = {c["name"] for c in inspect(connection).get_columns(table.name)}
            assert columns == set(table.columns.keys())
        assert connection.execute(text("SELECT COUNT(*) FROM plans")).scalar_one() == 3
        connection.execute(text("""INSERT INTO automation_whop_events(event_id,body_hash,handled_at)
            VALUES (:id,:hash,:now)"""), {"id":"synthetic-event","hash":"a"*64,"now":NOW})
        with pytest.raises(RuntimeError, match="records exist"):
            with Operations.context(MigrationContext.configure(connection)):
                migration.downgrade()
        connection.execute(text("DELETE FROM automation_whop_events WHERE event_id='synthetic-event'"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()
        assert connection.execute(text("SELECT COUNT(*) FROM users")).scalar_one() == 1


def test_parallel_checkouts_share_one_provider_configuration(setup):
    session,user,data,service,calls = setup
    engine = session.get_bind()
    if engine.dialect.name != "postgresql":
        pytest.skip("Cross-process advisory locks require disposable PostgreSQL")
    from concurrent.futures import ThreadPoolExecutor
    user_id = user.id
    def run_checkout(_):
        with Session(engine, expire_on_commit=False) as other:
            principal = other.get(User,user_id)
            return AutomationWhopService(other,service.provider).checkout(principal,"starter",uuid4())
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(run_checkout,range(3)))
    assert all(result == results[0] for result in results)
    assert len([r for r in calls if r.method == "POST"]) == 1


def test_signed_webhook_receipt_is_committed_with_access_and_replay_checked(setup, monkeypatch):
    import asyncio, base64, hashlib, hmac, time
    from app.api.routes import automation_whop as routes
    session,user,data,service,calls = setup
    start(setup)
    monkeypatch.setattr(settings,"AUTOMATION_WHOP_ACCOUNT_ID","biz_test")
    monkeypatch.setattr(settings,"AUTOMATION_WHOP_WEBHOOK_SECRET","ws_synthetic_test_secret")
    monkeypatch.setattr(routes,"adapter",lambda _: service.provider)
    monkeypatch.setattr(routes,"datetime",type("Clock",(),{"now":staticmethod(lambda _: NOW)}))
    def request(event_id="evt_synthetic", extra=None):
        raw = json.dumps({"id":event_id,"account_id":"biz_test","api_version":"v1",
            "api_version_date":"2026-11-11","type":"payment.succeeded","data":{"id":"pay_test"},
            **(extra or {})}).encode()
        stamp = str(int(time.time()))
        signature = base64.b64encode(hmac.new(settings.AUTOMATION_WHOP_WEBHOOK_SECRET.encode(),event_id.encode()+b"."+stamp.encode()+b"."+raw,hashlib.sha256).digest()).decode()
        class Request:
            headers = {"webhook-id":event_id,"webhook-timestamp":stamp,"webhook-signature":"v1,"+signature}
            async def stream(self):
                yield raw
        return Request()
    assert asyncio.run(routes.webhook(request(),session)) == {"received":True}
    assert effective_membership(session,user,NOW)
    count = len(calls)
    assert asyncio.run(routes.webhook(request(),session)) == {"received":True}
    assert len(calls) == count
    with pytest.raises(HTTPException) as error:
        asyncio.run(routes.webhook(request(extra={"changed":True}),session))
    assert error.value.status_code == 409
    # Failed authoritative lookups must leave no receipt to prevent webhook loss.
    data["/api/v1/payments/pay_test"]["metadata"] = {}
    with pytest.raises(HTTPException) as error:
        asyncio.run(routes.webhook(request("evt_retry"),session))
    assert error.value.status_code == 503
    assert session.get(AutomationWhopEvent,"evt_retry") is None


def test_whop_activation_disables_new_paddle_checkout(client, monkeypatch):
    monkeypatch.setattr(settings,"AUTOMATION_WHOP_ENABLED",True)
    response = client.post("/api/paddle/checkout",json={"plan_name":"Starter"})
    assert response.status_code == 410


def test_unconfigured_whop_checkout_is_not_live(client, monkeypatch):
    monkeypatch.setattr(settings,"AUTOMATION_WHOP_ENABLED",False)
    response = client.post("/api/whop/checkout",json={"plan_name":"starter","command_id":str(uuid4())})
    assert response.status_code == 503
