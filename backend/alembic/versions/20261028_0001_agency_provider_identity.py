"""Add provider-neutral Agency order references without removing Paddle history.

Revision ID: 20261028_0001
Revises: 20260831_0003
"""
from alembic import op
import sqlalchemy as sa

revision = "20261028_0001"
down_revision = "20260831_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agency_orders", sa.Column("payment_provider", sa.String(32), nullable=True))
    op.add_column("agency_orders", sa.Column("provider_order_id", sa.String(255), nullable=True))
    op.add_column("agency_orders", sa.Column("provider_product_id", sa.String(255), nullable=True))
    op.execute("""
        UPDATE agency_orders SET payment_provider = 'paddle',
            provider_order_id = paddle_transaction_id,
            provider_product_id = paddle_price_id
        WHERE paddle_transaction_id IS NOT NULL
    """)
    # Stop before NOT NULL if any legacy record lacks a Paddle identity.
    # No production rows are silently rewritten or discarded.
    bind = op.get_bind()
    unmatched = bind.execute(sa.text(
        "SELECT COUNT(*) FROM agency_orders "
        "WHERE payment_provider IS NULL OR provider_order_id IS NULL"
    )).scalar_one()
    if unmatched:
        raise RuntimeError(
            "Cannot migrate Agency orders with missing provider identity"
        )
    op.alter_column("agency_orders", "payment_provider", nullable=False,
                    existing_type=sa.String(32))
    op.alter_column("agency_orders", "provider_order_id", nullable=False,
                    existing_type=sa.String(255))
    op.create_unique_constraint(
        "uq_agency_orders_provider_identity",
        "agency_orders", ["payment_provider", "provider_order_id"],
    )
    op.alter_column("agency_orders", "paddle_transaction_id",
                    existing_type=sa.String(255), nullable=True)
    op.alter_column("agency_orders", "paddle_price_id",
                    existing_type=sa.String(255), nullable=True)


def downgrade() -> None:
    # Fail closed instead of destroying non-Paddle order identities.
    bind = op.get_bind()
    count = bind.execute(sa.text(
        "SELECT COUNT(*) FROM agency_orders WHERE payment_provider <> 'paddle'"
    )).scalar_one()
    if count:
        raise RuntimeError("Cannot downgrade while non-Paddle Agency orders exist")
    op.alter_column("agency_orders", "paddle_transaction_id",
                    existing_type=sa.String(255), nullable=False)
    op.alter_column("agency_orders", "paddle_price_id",
                    existing_type=sa.String(255), nullable=False)
    op.drop_constraint("uq_agency_orders_provider_identity", "agency_orders", type_="unique")
    for col in ("provider_product_id", "provider_order_id", "payment_provider"):
        op.drop_column("agency_orders", col)
