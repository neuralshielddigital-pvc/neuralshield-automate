"""lead crm fields

Revision ID: 20260509_0006
Revises: 20260509_0005
Create Date: 2026-05-09 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260509_0006"
down_revision: str | None = "20260509_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("campaign_leads", sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("campaign_leads", sa.Column("source", sa.String(length=120), nullable=True))
    op.add_column(
        "campaign_leads",
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
    )
    op.execute(
        """
        UPDATE campaign_leads
        SET user_id = users.id
        FROM users
        WHERE users.tenant_id = campaign_leads.tenant_id
          AND campaign_leads.user_id IS NULL
        """
    )
    op.alter_column("campaign_leads", "user_id", nullable=False)
    op.create_foreign_key(
        op.f("fk_campaign_leads_user_id_users"),
        "campaign_leads",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(op.f("ix_campaign_leads_user_id"), "campaign_leads", ["user_id"], unique=False)
    op.create_index(op.f("ix_campaign_leads_source"), "campaign_leads", ["source"], unique=False)
    op.alter_column("campaign_leads", "metadata", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_campaign_leads_source"), table_name="campaign_leads")
    op.drop_index(op.f("ix_campaign_leads_user_id"), table_name="campaign_leads")
    op.drop_constraint(op.f("fk_campaign_leads_user_id_users"), "campaign_leads", type_="foreignkey")
    op.drop_column("campaign_leads", "metadata")
    op.drop_column("campaign_leads", "source")
    op.drop_column("campaign_leads", "user_id")
