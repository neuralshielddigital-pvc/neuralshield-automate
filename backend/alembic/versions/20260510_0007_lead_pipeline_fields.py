"""lead pipeline fields

Revision ID: 20260510_0007
Revises: f3d358500c2c
Create Date: 2026-05-10 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260510_0007"
down_revision: str | None = "f3d358500c2c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


lead_stage = sa.Enum("NEW", "CONTACTED", "QUALIFIED", "WON", "LOST", name="lead_stage")


def upgrade() -> None:
    bind = op.get_bind()
    lead_stage.create(bind, checkfirst=True)

    op.add_column("campaign_leads", sa.Column("stage", lead_stage, server_default="NEW", nullable=False))
    op.add_column("campaign_leads", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("campaign_leads", sa.Column("last_contacted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_campaign_leads_stage"), "campaign_leads", ["stage"], unique=False)
    op.alter_column("campaign_leads", "stage", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_campaign_leads_stage"), table_name="campaign_leads")
    op.drop_column("campaign_leads", "last_contacted_at")
    op.drop_column("campaign_leads", "notes")
    op.drop_column("campaign_leads", "stage")

    bind = op.get_bind()
    lead_stage.drop(bind, checkfirst=True)
