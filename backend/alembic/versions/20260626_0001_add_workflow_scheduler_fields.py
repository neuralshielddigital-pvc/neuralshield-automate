"""add workflow scheduler fields

Revision ID: 20260626_0001
Revises: 20260510_0008
Create Date: 2026-06-26
"""

from alembic import op
import sqlalchemy as sa


revision = "20260626_0001"
down_revision = "20260510_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workflows", sa.Column("schedule_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("workflows", sa.Column("schedule_cron", sa.String(length=120), nullable=True))
    op.add_column("workflows", sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("workflows", sa.Column("last_scheduled_run_at", sa.DateTime(timezone=True), nullable=True))

    op.create_index("ix_workflows_schedule_enabled", "workflows", ["schedule_enabled"])
    op.create_index("ix_workflows_next_run_at", "workflows", ["next_run_at"])

    op.alter_column("workflows", "schedule_enabled", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_workflows_next_run_at", table_name="workflows")
    op.drop_index("ix_workflows_schedule_enabled", table_name="workflows")

    op.drop_column("workflows", "last_scheduled_run_at")
    op.drop_column("workflows", "next_run_at")
    op.drop_column("workflows", "schedule_cron")
    op.drop_column("workflows", "schedule_enabled")
