"""zapier workflow automation

Revision ID: 20260509_0004
Revises: 20260509_0003
Create Date: 2026-05-09 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260509_0004"
down_revision: str | None = "20260509_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


workflow_trigger_type = sa.Enum(
    "WEBHOOK_RECEIVED",
    "NEW_LEAD",
    "CAMPAIGN_ACTIVATED",
    name="workflow_trigger_type",
)
workflow_action_type = sa.Enum(
    "SEND_WEBHOOK",
    "CREATE_LEAD",
    "ADD_AUDIT_LOG",
    name="workflow_action_type",
)


def upgrade() -> None:
    bind = op.get_bind()
    workflow_trigger_type.create(bind, checkfirst=True)
    workflow_action_type.create(bind, checkfirst=True)

    op.add_column("workflows", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("workflows", sa.Column("public_webhook_key", sa.String(length=160), nullable=True))
    op.execute("UPDATE workflows SET public_webhook_key = 'wf_' || replace(id::text, '-', '') WHERE public_webhook_key IS NULL")
    op.alter_column("workflows", "public_webhook_key", nullable=False)
    op.create_index(op.f("ix_workflows_public_webhook_key"), "workflows", ["public_webhook_key"], unique=True)

    op.drop_index(op.f("ix_workflow_triggers_type"), table_name="workflow_triggers")
    op.add_column(
        "workflow_triggers",
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
    )
    op.add_column("workflow_triggers", sa.Column("type_new", workflow_trigger_type, nullable=True))
    op.execute(
        """
        UPDATE workflow_triggers
        SET type_new = CASE
            WHEN type = 'WEBHOOK_RECEIVED' THEN 'WEBHOOK_RECEIVED'::workflow_trigger_type
            WHEN type = 'NEW_LEAD' THEN 'NEW_LEAD'::workflow_trigger_type
            WHEN type = 'CAMPAIGN_ACTIVATED' THEN 'CAMPAIGN_ACTIVATED'::workflow_trigger_type
            ELSE 'WEBHOOK_RECEIVED'::workflow_trigger_type
        END
        """
    )
    op.drop_column("workflow_triggers", "type")
    op.alter_column("workflow_triggers", "type_new", new_column_name="type", nullable=False)
    op.create_index(op.f("ix_workflow_triggers_type"), "workflow_triggers", ["type"], unique=False)

    op.drop_index(op.f("ix_workflow_actions_type"), table_name="workflow_actions")
    op.add_column(
        "workflow_actions",
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
    )
    op.add_column("workflow_actions", sa.Column("type_new", workflow_action_type, nullable=True))
    op.execute(
        """
        UPDATE workflow_actions
        SET type_new = CASE
            WHEN type = 'SEND_WEBHOOK' THEN 'SEND_WEBHOOK'::workflow_action_type
            WHEN type = 'CREATE_LEAD' THEN 'CREATE_LEAD'::workflow_action_type
            WHEN type = 'ADD_AUDIT_LOG' THEN 'ADD_AUDIT_LOG'::workflow_action_type
            ELSE 'ADD_AUDIT_LOG'::workflow_action_type
        END
        """
    )
    op.drop_column("workflow_actions", "type")
    op.alter_column("workflow_actions", "type_new", new_column_name="type", nullable=False)
    op.create_index(op.f("ix_workflow_actions_type"), "workflow_actions", ["type"], unique=False)

    op.add_column(
        "workflow_runs",
        sa.Column("trigger_payload", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
    )

    op.alter_column("workflow_triggers", "config", server_default=None)
    op.alter_column("workflow_actions", "config", server_default=None)
    op.alter_column("workflow_runs", "trigger_payload", server_default=None)


def downgrade() -> None:
    op.drop_column("workflow_runs", "trigger_payload")

    op.drop_index(op.f("ix_workflow_actions_type"), table_name="workflow_actions")
    op.add_column("workflow_actions", sa.Column("type_text", sa.String(length=80), nullable=True))
    op.execute("UPDATE workflow_actions SET type_text = type::text")
    op.drop_column("workflow_actions", "type")
    op.alter_column("workflow_actions", "type_text", new_column_name="type", nullable=False)
    op.drop_column("workflow_actions", "config")
    op.create_index(op.f("ix_workflow_actions_type"), "workflow_actions", ["type"], unique=False)

    op.drop_index(op.f("ix_workflow_triggers_type"), table_name="workflow_triggers")
    op.add_column("workflow_triggers", sa.Column("type_text", sa.String(length=80), nullable=True))
    op.execute("UPDATE workflow_triggers SET type_text = type::text")
    op.drop_column("workflow_triggers", "type")
    op.alter_column("workflow_triggers", "type_text", new_column_name="type", nullable=False)
    op.drop_column("workflow_triggers", "config")
    op.create_index(op.f("ix_workflow_triggers_type"), "workflow_triggers", ["type"], unique=False)

    op.drop_index(op.f("ix_workflows_public_webhook_key"), table_name="workflows")
    op.drop_column("workflows", "public_webhook_key")
    op.drop_column("workflows", "description")

    bind = op.get_bind()
    workflow_action_type.drop(bind, checkfirst=True)
    workflow_trigger_type.drop(bind, checkfirst=True)
