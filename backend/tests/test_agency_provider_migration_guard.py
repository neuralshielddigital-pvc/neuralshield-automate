"""Repository-only migration contract tests (no database or AWS calls)."""
from pathlib import Path


def test_provider_migration_fails_closed_on_unmapped_legacy_rows():
    file = (
        Path(__file__).resolve().parents[1]
        / "alembic/versions/20261028_0001_agency_provider_identity.py"
    )
    source = file.read_text(encoding="utf-8")
    assert "WHERE payment_provider IS NULL OR provider_order_id IS NULL" in source
    assert "Cannot migrate Agency orders with missing provider identity" in source
    assert source.index("if unmatched:") < source.index(
        'op.alter_column("agency_orders", "payment_provider", nullable=False'
    )
    assert "WHERE paddle_transaction_id IS NOT NULL" in source


def test_migration_retains_paddle_identity_and_downgrade_guard():
    file = (
        Path(__file__).resolve().parents[1]
        / "alembic/versions/20261028_0001_agency_provider_identity.py"
    )
    source = file.read_text(encoding="utf-8")
    assert "provider_order_id = paddle_transaction_id" in source
    assert "provider_product_id = paddle_price_id" in source
    assert "Cannot downgrade while non-Paddle Agency orders exist" in source
