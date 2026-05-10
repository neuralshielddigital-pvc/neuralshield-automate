"""create core models

Revision ID: 20260505_0001
Revises:
Create Date: 2026-05-05 23:55:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260505_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


user_role = sa.Enum("USER", "ADMIN", "SUPER_ADMIN", name="user_role")
tenant_user_role = sa.Enum("USER", "ADMIN", "SUPER_ADMIN", name="tenant_user_role")
plan_interval = sa.Enum("monthly", "yearly", name="plan_interval")
subscription_status = sa.Enum(
    "ACTIVE",
    "CANCELED",
    "PAST_DUE",
    "INCOMPLETE",
    name="subscription_status",
)
commission_status = sa.Enum(
    "PENDING",
    "APPROVED",
    "REJECTED",
    "PAID",
    name="commission_status",
)
campaign_status = sa.Enum(
    "DRAFT",
    "RUNNING",
    "PAUSED",
    "COMPLETED",
    name="campaign_status",
)
workflow_run_status = sa.Enum(
    "QUEUED",
    "RUNNING",
    "COMPLETED",
    "FAILED",
    name="workflow_run_status",
)


def timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        *timestamp_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tenants")),
    )
    op.create_index(op.f("ix_tenants_name"), "tenants", ["name"], unique=False)

    op.create_table(
        "plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("stripe_price_id", sa.String(length=255), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("interval", plan_interval, nullable=False),
        *timestamp_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_plans")),
    )
    op.create_index(op.f("ix_plans_name"), "plans", ["name"], unique=False)
    op.create_index(op.f("ix_plans_stripe_price_id"), "plans", ["stripe_price_id"], unique=True)

    op.create_table(
        "admin_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=150), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        *timestamp_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_admin_settings")),
    )
    op.create_index(op.f("ix_admin_settings_key"), "admin_settings", ["key"], unique=True)

    op.create_table(
        "webhook_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=150), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("processed", sa.Boolean(), nullable=False),
        *timestamp_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_webhook_events")),
    )
    op.create_index(op.f("ix_webhook_events_event_id"), "webhook_events", ["event_id"], unique=True)
    op.create_index(op.f("ix_webhook_events_processed"), "webhook_events", ["processed"], unique=False)
    op.create_index(op.f("ix_webhook_events_type"), "webhook_events", ["type"], unique=False)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_users_tenant_id_tenants"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_tenant_id"), "users", ["tenant_id"], unique=False)

    op.create_table(
        "tenant_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", tenant_user_role, nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_tenant_users_tenant_id_tenants"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_tenant_users_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tenant_users")),
        sa.UniqueConstraint("user_id", "tenant_id", name="uq_tenant_users_user_id_tenant_id"),
    )
    op.create_index(op.f("ix_tenant_users_tenant_id"), "tenant_users", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_tenant_users_user_id"), "tenant_users", ["user_id"], unique=False)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_refresh_tokens_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_refresh_tokens_token_hash")),
    )
    op.create_index(op.f("ix_refresh_tokens_expires_at"), "refresh_tokens", ["expires_at"], unique=False)
    op.create_index(op.f("ix_refresh_tokens_revoked"), "refresh_tokens", ["revoked"], unique=False)
    op.create_index(op.f("ix_refresh_tokens_user_id"), "refresh_tokens", ["user_id"], unique=False)

    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=False),
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", subscription_status, nullable=False),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], name=op.f("fk_subscriptions_plan_id_plans"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_subscriptions_tenant_id_tenants"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_subscriptions_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_subscriptions")),
    )
    op.create_index(op.f("ix_subscriptions_current_period_end"), "subscriptions", ["current_period_end"], unique=False)
    op.create_index(op.f("ix_subscriptions_plan_id"), "subscriptions", ["plan_id"], unique=False)
    op.create_index(op.f("ix_subscriptions_status"), "subscriptions", ["status"], unique=False)
    op.create_index(op.f("ix_subscriptions_stripe_customer_id"), "subscriptions", ["stripe_customer_id"], unique=False)
    op.create_index(op.f("ix_subscriptions_stripe_subscription_id"), "subscriptions", ["stripe_subscription_id"], unique=True)
    op.create_index(op.f("ix_subscriptions_tenant_id"), "subscriptions", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_subscriptions_user_id"), "subscriptions", ["user_id"], unique=False)

    op.create_table(
        "affiliates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("referral_code", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_affiliates_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_affiliates")),
    )
    op.create_index(op.f("ix_affiliates_is_active"), "affiliates", ["is_active"], unique=False)
    op.create_index(op.f("ix_affiliates_referral_code"), "affiliates", ["referral_code"], unique=True)
    op.create_index(op.f("ix_affiliates_user_id"), "affiliates", ["user_id"], unique=True)

    op.create_table(
        "campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("status", campaign_status, nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_campaigns_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_campaigns")),
    )
    op.create_index(op.f("ix_campaigns_name"), "campaigns", ["name"], unique=False)
    op.create_index(op.f("ix_campaigns_status"), "campaigns", ["status"], unique=False)
    op.create_index(op.f("ix_campaigns_user_id"), "campaigns", ["user_id"], unique=False)

    op.create_table(
        "contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_contacts_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_contacts")),
        sa.UniqueConstraint("user_id", "email", name="uq_contacts_user_id_email"),
    )
    op.create_index(op.f("ix_contacts_email"), "contacts", ["email"], unique=False)
    op.create_index(op.f("ix_contacts_user_id"), "contacts", ["user_id"], unique=False)

    op.create_table(
        "workflows",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_workflows_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workflows")),
    )
    op.create_index(op.f("ix_workflows_is_active"), "workflows", ["is_active"], unique=False)
    op.create_index(op.f("ix_workflows_name"), "workflows", ["name"], unique=False)
    op.create_index(op.f("ix_workflows_user_id"), "workflows", ["user_id"], unique=False)

    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key_hash", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_api_keys_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_api_keys")),
    )
    op.create_index(op.f("ix_api_keys_key_hash"), "api_keys", ["key_hash"], unique=True)
    op.create_index(op.f("ix_api_keys_revoked"), "api_keys", ["revoked"], unique=False)
    op.create_index(op.f("ix_api_keys_user_id"), "api_keys", ["user_id"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_audit_logs_user_id_users"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
    )
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"], unique=False)
    op.create_index(op.f("ix_audit_logs_user_id"), "audit_logs", ["user_id"], unique=False)

    op.create_table(
        "referrals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("affiliate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("referred_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["affiliate_id"], ["affiliates.id"], name=op.f("fk_referrals_affiliate_id_affiliates"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["referred_user_id"], ["users.id"], name=op.f("fk_referrals_referred_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_referrals")),
        sa.UniqueConstraint("affiliate_id", "referred_user_id", name="uq_referrals_affiliate_id_referred_user_id"),
    )
    op.create_index(op.f("ix_referrals_affiliate_id"), "referrals", ["affiliate_id"], unique=False)
    op.create_index(op.f("ix_referrals_referred_user_id"), "referrals", ["referred_user_id"], unique=False)

    op.create_table(
        "workflow_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(length=80), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], name=op.f("fk_workflow_actions_workflow_id_workflows"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workflow_actions")),
    )
    op.create_index(op.f("ix_workflow_actions_type"), "workflow_actions", ["type"], unique=False)
    op.create_index(op.f("ix_workflow_actions_workflow_id"), "workflow_actions", ["workflow_id"], unique=False)

    op.create_table(
        "workflow_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", workflow_run_status, nullable=False),
        sa.Column("logs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], name=op.f("fk_workflow_runs_workflow_id_workflows"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workflow_runs")),
    )
    op.create_index(op.f("ix_workflow_runs_status"), "workflow_runs", ["status"], unique=False)
    op.create_index(op.f("ix_workflow_runs_workflow_id"), "workflow_runs", ["workflow_id"], unique=False)

    op.create_table(
        "workflow_triggers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(length=80), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], name=op.f("fk_workflow_triggers_workflow_id_workflows"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workflow_triggers")),
    )
    op.create_index(op.f("ix_workflow_triggers_type"), "workflow_triggers", ["type"], unique=False)
    op.create_index(op.f("ix_workflow_triggers_workflow_id"), "workflow_triggers", ["workflow_id"], unique=False)

    op.create_table(
        "commissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("affiliate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("referral_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", commission_status, nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["affiliate_id"], ["affiliates.id"], name=op.f("fk_commissions_affiliate_id_affiliates"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["referral_id"], ["referrals.id"], name=op.f("fk_commissions_referral_id_referrals"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_commissions")),
    )
    op.create_index(op.f("ix_commissions_affiliate_id"), "commissions", ["affiliate_id"], unique=False)
    op.create_index(op.f("ix_commissions_referral_id"), "commissions", ["referral_id"], unique=False)
    op.create_index(op.f("ix_commissions_status"), "commissions", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_commissions_status"), table_name="commissions")
    op.drop_index(op.f("ix_commissions_referral_id"), table_name="commissions")
    op.drop_index(op.f("ix_commissions_affiliate_id"), table_name="commissions")
    op.drop_table("commissions")

    op.drop_index(op.f("ix_workflow_triggers_workflow_id"), table_name="workflow_triggers")
    op.drop_index(op.f("ix_workflow_triggers_type"), table_name="workflow_triggers")
    op.drop_table("workflow_triggers")

    op.drop_index(op.f("ix_workflow_runs_workflow_id"), table_name="workflow_runs")
    op.drop_index(op.f("ix_workflow_runs_status"), table_name="workflow_runs")
    op.drop_table("workflow_runs")

    op.drop_index(op.f("ix_workflow_actions_workflow_id"), table_name="workflow_actions")
    op.drop_index(op.f("ix_workflow_actions_type"), table_name="workflow_actions")
    op.drop_table("workflow_actions")

    op.drop_index(op.f("ix_referrals_referred_user_id"), table_name="referrals")
    op.drop_index(op.f("ix_referrals_affiliate_id"), table_name="referrals")
    op.drop_table("referrals")

    op.drop_index(op.f("ix_audit_logs_user_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_action"), table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index(op.f("ix_api_keys_user_id"), table_name="api_keys")
    op.drop_index(op.f("ix_api_keys_revoked"), table_name="api_keys")
    op.drop_index(op.f("ix_api_keys_key_hash"), table_name="api_keys")
    op.drop_table("api_keys")

    op.drop_index(op.f("ix_workflows_user_id"), table_name="workflows")
    op.drop_index(op.f("ix_workflows_name"), table_name="workflows")
    op.drop_index(op.f("ix_workflows_is_active"), table_name="workflows")
    op.drop_table("workflows")

    op.drop_index(op.f("ix_contacts_user_id"), table_name="contacts")
    op.drop_index(op.f("ix_contacts_email"), table_name="contacts")
    op.drop_table("contacts")

    op.drop_index(op.f("ix_campaigns_user_id"), table_name="campaigns")
    op.drop_index(op.f("ix_campaigns_status"), table_name="campaigns")
    op.drop_index(op.f("ix_campaigns_name"), table_name="campaigns")
    op.drop_table("campaigns")

    op.drop_index(op.f("ix_affiliates_user_id"), table_name="affiliates")
    op.drop_index(op.f("ix_affiliates_referral_code"), table_name="affiliates")
    op.drop_index(op.f("ix_affiliates_is_active"), table_name="affiliates")
    op.drop_table("affiliates")

    op.drop_index(op.f("ix_subscriptions_user_id"), table_name="subscriptions")
    op.drop_index(op.f("ix_subscriptions_tenant_id"), table_name="subscriptions")
    op.drop_index(op.f("ix_subscriptions_stripe_subscription_id"), table_name="subscriptions")
    op.drop_index(op.f("ix_subscriptions_stripe_customer_id"), table_name="subscriptions")
    op.drop_index(op.f("ix_subscriptions_status"), table_name="subscriptions")
    op.drop_index(op.f("ix_subscriptions_plan_id"), table_name="subscriptions")
    op.drop_index(op.f("ix_subscriptions_current_period_end"), table_name="subscriptions")
    op.drop_table("subscriptions")

    op.drop_index(op.f("ix_refresh_tokens_user_id"), table_name="refresh_tokens")
    op.drop_index(op.f("ix_refresh_tokens_revoked"), table_name="refresh_tokens")
    op.drop_index(op.f("ix_refresh_tokens_expires_at"), table_name="refresh_tokens")
    op.drop_table("refresh_tokens")

    op.drop_index(op.f("ix_tenant_users_user_id"), table_name="tenant_users")
    op.drop_index(op.f("ix_tenant_users_tenant_id"), table_name="tenant_users")
    op.drop_table("tenant_users")

    op.drop_index(op.f("ix_users_tenant_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

    op.drop_index(op.f("ix_webhook_events_type"), table_name="webhook_events")
    op.drop_index(op.f("ix_webhook_events_processed"), table_name="webhook_events")
    op.drop_index(op.f("ix_webhook_events_event_id"), table_name="webhook_events")
    op.drop_table("webhook_events")

    op.drop_index(op.f("ix_admin_settings_key"), table_name="admin_settings")
    op.drop_table("admin_settings")

    op.drop_index(op.f("ix_plans_stripe_price_id"), table_name="plans")
    op.drop_index(op.f("ix_plans_name"), table_name="plans")
    op.drop_table("plans")

    op.drop_index(op.f("ix_tenants_name"), table_name="tenants")
    op.drop_table("tenants")

    bind = op.get_bind()
    workflow_run_status.drop(bind, checkfirst=True)
    campaign_status.drop(bind, checkfirst=True)
    commission_status.drop(bind, checkfirst=True)
    subscription_status.drop(bind, checkfirst=True)
    plan_interval.drop(bind, checkfirst=True)
    tenant_user_role.drop(bind, checkfirst=True)
    user_role.drop(bind, checkfirst=True)
