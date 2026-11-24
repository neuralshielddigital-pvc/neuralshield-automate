"""Isolated, default-deny Whop SaaS subscription binding table.

Revision ID: 20261116_0001
Revises: 20261028_0001
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "20261116_0001"
down_revision = "20261028_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "whop_saas_subscription_bindings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider_subscription_id", sa.String(255), nullable=False),
        sa.Column("provider_customer_id", sa.String(255), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("tier", sa.String(32), nullable=False, server_default="unverified"),
        sa.Column("access_state", sa.String(32), nullable=False, server_default="inactive"),
        sa.Column("access_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("provider_observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("provider_subscription_id", name="uq_whop_saas_subscription_bindings_provider_subscription_id"),
    )
    for column in ("provider_subscription_id", "provider_customer_id", "tenant_id", "user_id"):
        op.create_index(
            f"ix_whop_saas_subscription_bindings_{column}",
            "whop_saas_subscription_bindings", [column]
        )


def downgrade() -> None:
    # Never silently destroy verified customer relationships or entitlements.
    bind = op.get_bind()
    num_rows = bind.execute(sa.text("SELECT COUNT(*) FROM whop_saas_subscription_bindings")).scalar_one()
    if num_rows:
        raise RuntimeError("Refusing downgrade: SaaS subscription bindings exist")
    op.drop_table("whop_saas_subscription_bindings")
