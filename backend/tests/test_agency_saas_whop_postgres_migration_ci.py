"""Exercise SaaS Whop migration on isolated CI PostgreSQL only."""
import importlib.util
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.dialects.postgresql import UUID


def test_whop_saas_binding_migration_is_default_deny_and_refuses_data_loss():
    url = os.environ.get("AGENCY_WHOP_TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("Disposable CI PostgreSQL required")
    if not url.startswith("postgresql") or "127.0.0.1:55432/" not in url:
        pytest.fail("Whop migration restricted to isolated CI PostgreSQL")

    module_path = (
        Path(__file__).resolve().parents[1] / "alembic" / "versions"
        / "20261116_0001_whop_saas_subscription_bindings.py"
    )
    spec = importlib.util.spec_from_file_location("whop_saas_ci_migration", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    engine = sa.create_engine(url)
    metadata = sa.MetaData()
    tenants = sa.Table(
        "tenants", metadata, sa.Column("id", UUID(as_uuid=True), primary_key=True)
    )
    users = sa.Table(
        "users", metadata, sa.Column("id", UUID(as_uuid=True), primary_key=True)
    )
    tenant_id = uuid4()
    user_id = uuid4()
    subscription_id = f"sub_ci_{uuid4().hex}"
    try:
        metadata.create_all(engine, tables=[tenants, users])
        with engine.begin() as connection:
            connection.execute(tenants.insert().values(id=tenant_id))
            connection.execute(users.insert().values(id=user_id))
            context = MigrationContext.configure(connection)
            with Operations.context(context):
                module.upgrade()
            columns = {c["name"] for c in sa.inspect(connection).get_columns(
                "whop_saas_subscription_bindings"
            )}
            assert {"access_enabled", "provider_observed_at", "tenant_id", "user_id"} <= columns
            connection.execute(sa.text("""
                INSERT INTO whop_saas_subscription_bindings
                (id, created_at, updated_at,
                 provider_subscription_id, provider_customer_id, tenant_id, user_id)
                VALUES (:id, :when, :when, :subscription, :customer, :tenant, :user)
            """), {
                "id": uuid4(), "when": datetime.now(timezone.utc),
                "subscription": subscription_id, "customer": "cus_ci",
                "tenant": tenant_id, "user": user_id,
            })
            row = connection.execute(sa.text("""
                SELECT tier, access_state, access_enabled
                FROM whop_saas_subscription_bindings
                WHERE provider_subscription_id = :subscription
            """), {"subscription": subscription_id}).one()
            assert row == ("unverified", "inactive", False)
            with pytest.raises(RuntimeError, match="bindings exist"):
                with Operations.context(context):
                    module.downgrade()
            connection.execute(sa.text("""
                DELETE FROM whop_saas_subscription_bindings
                WHERE provider_subscription_id = :subscription
            """), {"subscription": subscription_id})
            with Operations.context(context):
                module.downgrade()
            assert "whop_saas_subscription_bindings" not in sa.inspect(connection).get_table_names()
    finally:
        metadata.drop_all(engine, checkfirst=True)
        engine.dispose()
