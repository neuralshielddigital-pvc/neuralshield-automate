"""Run the Agency provider migration on disposable CI PostgreSQL only.

Exercises actual Alembic upgrade/backfill/downgrade operations, without any
production database connection.
"""
import importlib.util
import os
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_agency_provider_migration_backfills_legacy_paddle_orders():
    url = os.environ.get("AGENCY_WHOP_TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("Dedicated disposable PostgreSQL required")
    if not url.startswith("postgresql") or "127.0.0.1:55432/" not in url:
        pytest.fail("Migration test restricted to CI loopback PostgreSQL port 55432")

    migration_path = (
        Path(__file__).resolve().parents[1] / "alembic" / "versions"
        / "20261028_0001_agency_provider_identity.py"
    )
    spec = importlib.util.spec_from_file_location("agency_provider_migration", migration_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    engine = sa.create_engine(url)
    metadata = sa.MetaData()
    table = sa.Table(
        "agency_orders", metadata,
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("paddle_transaction_id", sa.String(255), nullable=False, unique=True),
        sa.Column("paddle_price_id", sa.String(255), nullable=False),
    )
    try:
        metadata.create_all(engine)
        transaction_id = "txn_ci_" + uuid4().hex
        with engine.begin() as connection:
            connection.execute(
                table.insert().values(
                    id="legacy", paddle_transaction_id=transaction_id,
                    paddle_price_id="pri_synthetic",
                )
            )
            context = MigrationContext.configure(connection)
            with Operations.context(context):
                module.upgrade()
            result = connection.execute(sa.text(
                "SELECT payment_provider, provider_order_id, provider_product_id "
                "FROM agency_orders WHERE id = 'legacy'"
            )).one()
            assert result == ("paddle", transaction_id, "pri_synthetic")
            with Operations.context(context):
                module.downgrade()
        columns = [c["name"] for c in sa.inspect(engine).get_columns("agency_orders")]
        assert "payment_provider" not in columns
        assert "paddle_transaction_id" in columns
    finally:
        metadata.drop_all(engine, checkfirst=True)
        engine.dispose()
