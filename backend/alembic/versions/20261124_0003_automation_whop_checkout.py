"""Durable Automation checkout ownership and verified paid periods; no grants."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "20261124_0003"
down_revision = "20261122_0002"
branch_labels = None
depends_on = None


def timestamps():
    return [sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False)]


def owner_columns():
    return [sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False)]


def upgrade():
    op.create_table("automation_whop_intents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True), *owner_columns(), *timestamps(),
        sa.Column("command_id", sa.String(36), nullable=False),
        sa.Column("plan_code", sa.String(24), nullable=False),
        sa.Column("catalog_version", sa.String(80), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("configuration_id", sa.String(255), nullable=True, unique=True),
        sa.Column("checkout_url", sa.String(1024), nullable=True),
        sa.UniqueConstraint("user_id", "command_id", name="uq_automation_whop_command"),
        sa.CheckConstraint("amount_minor > 0", name="positive_amount"),
        sa.CheckConstraint("plan_code IN ('starter','pro','business')", name="allowed_plan"))
    op.create_table("automation_whop_memberships",
        sa.Column("membership_id", sa.String(255), primary_key=True), *owner_columns(), *timestamps(),
        sa.Column("intent_id", UUID(as_uuid=True), sa.ForeignKey("automation_whop_intents.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("customer_id", sa.String(255), nullable=False),
        sa.Column("plan_code", sa.String(24), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("terminal", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("current_period_start", sa.DateTime(timezone=True)),
        sa.Column("current_period_end", sa.DateTime(timezone=True)),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("NOT active OR (NOT terminal AND current_period_start IS NOT NULL AND current_period_end > current_period_start)", name="paid_period_required"))
    op.create_table("automation_whop_payments", *timestamps(),
        sa.Column("payment_id", sa.String(255), primary_key=True),
        sa.Column("membership_id", sa.String(255), sa.ForeignKey("automation_whop_memberships.membership_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("intent_id", UUID(as_uuid=True), sa.ForeignKey("automation_whop_intents.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table("automation_whop_events",
        sa.Column("event_id", sa.String(255), primary_key=True),
        sa.Column("body_hash", sa.String(64), nullable=False),
        sa.Column("handled_at", sa.DateTime(timezone=True), nullable=False))
    for table, columns in {
        "automation_whop_intents": ["user_id", "tenant_id"],
        "automation_whop_memberships": ["user_id", "tenant_id", "intent_id", "checked_at"],
        "automation_whop_payments": ["membership_id"],
    }.items():
        for column in columns:
            op.create_index("ix_" + table + "_" + column, table, [column])


def downgrade():
    bind = op.get_bind()
    tables = ["automation_whop_events", "automation_whop_payments", "automation_whop_memberships", "automation_whop_intents"]
    for table in tables:
        if bind.execute(sa.text("SELECT COUNT(*) FROM " + table)).scalar_one():
            raise RuntimeError("Refusing downgrade: Automation billing records exist")
    for table in tables:
        op.drop_table(table)
