"""campaign automation engine

Revision ID: 20260509_0003
Revises: 5de10b036ecc
Create Date: 2026-05-09 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260509_0003"
down_revision: str | None = "5de10b036ecc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


campaign_type = sa.Enum("EMAIL", "SMS", "WHATSAPP", name="campaign_type")
campaign_execution_status = sa.Enum("PENDING", "SUCCESS", "FAILED", name="campaign_execution_status")


def upgrade() -> None:
    bind = op.get_bind()
    campaign_type.create(bind, checkfirst=True)

    op.execute(
        """
        DO $$
        BEGIN
            ALTER TYPE campaign_status ADD VALUE IF NOT EXISTS 'ACTIVE';
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )

    op.add_column("campaigns", sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("campaigns", sa.Column("type", campaign_type, server_default="EMAIL", nullable=False))
    op.add_column("campaigns", sa.Column("subject", sa.String(length=255), nullable=True))
    op.add_column("campaigns", sa.Column("message", sa.Text(), server_default="", nullable=False))
    op.execute(
        """
        UPDATE campaigns
        SET tenant_id = users.tenant_id
        FROM users
        WHERE campaigns.user_id = users.id
          AND campaigns.tenant_id IS NULL
        """
    )
    op.alter_column("campaigns", "tenant_id", nullable=False)
    op.create_foreign_key(
        op.f("fk_campaigns_tenant_id_tenants"),
        "campaigns",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(op.f("ix_campaigns_tenant_id"), "campaigns", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_campaigns_type"), "campaigns", ["type"], unique=False)

    op.add_column("workflows", sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("workflows", sa.Column("definition", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False))
    op.execute(
        """
        UPDATE workflows
        SET tenant_id = users.tenant_id
        FROM users
        WHERE workflows.user_id = users.id
          AND workflows.tenant_id IS NULL
        """
    )
    op.alter_column("workflows", "tenant_id", nullable=False)
    op.create_foreign_key(
        op.f("fk_workflows_tenant_id_tenants"),
        "workflows",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(op.f("ix_workflows_tenant_id"), "workflows", ["tenant_id"], unique=False)

    op.create_table(
        "campaign_leads",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_campaign_leads_tenant_id_tenants"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_campaign_leads")),
        sa.UniqueConstraint("tenant_id", "email", name="uq_campaign_leads_tenant_id_email"),
    )
    op.create_index(op.f("ix_campaign_leads_email"), "campaign_leads", ["email"], unique=False)
    op.create_index(op.f("ix_campaign_leads_tenant_id"), "campaign_leads", ["tenant_id"], unique=False)

    op.create_table(
        "campaign_executions",
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", campaign_execution_status, nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("response_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], name=op.f("fk_campaign_executions_campaign_id_campaigns"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lead_id"], ["campaign_leads.id"], name=op.f("fk_campaign_executions_lead_id_campaign_leads"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_campaign_executions")),
    )
    op.create_index(op.f("ix_campaign_executions_campaign_id"), "campaign_executions", ["campaign_id"], unique=False)
    op.create_index(op.f("ix_campaign_executions_lead_id"), "campaign_executions", ["lead_id"], unique=False)
    op.create_index(op.f("ix_campaign_executions_status"), "campaign_executions", ["status"], unique=False)

    op.alter_column("campaigns", "type", server_default=None)
    op.alter_column("campaigns", "message", server_default=None)
    op.alter_column("workflows", "definition", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_campaign_executions_status"), table_name="campaign_executions")
    op.drop_index(op.f("ix_campaign_executions_lead_id"), table_name="campaign_executions")
    op.drop_index(op.f("ix_campaign_executions_campaign_id"), table_name="campaign_executions")
    op.drop_table("campaign_executions")

    op.drop_index(op.f("ix_campaign_leads_tenant_id"), table_name="campaign_leads")
    op.drop_index(op.f("ix_campaign_leads_email"), table_name="campaign_leads")
    op.drop_table("campaign_leads")

    op.drop_index(op.f("ix_workflows_tenant_id"), table_name="workflows")
    op.drop_constraint(op.f("fk_workflows_tenant_id_tenants"), "workflows", type_="foreignkey")
    op.drop_column("workflows", "definition")
    op.drop_column("workflows", "tenant_id")

    op.drop_index(op.f("ix_campaigns_type"), table_name="campaigns")
    op.drop_index(op.f("ix_campaigns_tenant_id"), table_name="campaigns")
    op.drop_constraint(op.f("fk_campaigns_tenant_id_tenants"), "campaigns", type_="foreignkey")
    op.drop_column("campaigns", "message")
    op.drop_column("campaigns", "subject")
    op.drop_column("campaigns", "type")
    op.drop_column("campaigns", "tenant_id")

    bind = op.get_bind()
    campaign_execution_status.drop(bind, checkfirst=True)
    campaign_type.drop(bind, checkfirst=True)
