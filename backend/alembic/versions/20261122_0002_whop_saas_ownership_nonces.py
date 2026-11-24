"""Persistent single-use Whop SaaS ownership authorization nonces.

Revision ID: 20261122_0002
Revises: 20261116_0001

Stores only opaque authorization identifiers, never provider tokens or secrets.
No subscription entitlement is granted by this migration.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261122_0002"
down_revision = "20261116_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "whop_saas_ownership_nonces",
        sa.Column("nonce", sa.String(256), primary_key=True, nullable=False),
        sa.Column("session_id", sa.String(256), nullable=False),
        sa.Column("user_id", sa.String(256), nullable=False),
        sa.Column("tenant_id", sa.String(256), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("length(nonce) >= 16", name="ck_whop_saas_nonce_length"),
        sa.CheckConstraint("length(session_id) >= 16", name="ck_whop_saas_session_length"),
    )
    op.create_index(
        "ix_whop_saas_ownership_nonces_expires_at",
        "whop_saas_ownership_nonces",
        ["expires_at"],
    )


def downgrade() -> None:
    # Do not invalidate live, unexpired authorizations silently.
    bind = op.get_bind()
    active = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM whop_saas_ownership_nonces "
            "WHERE consumed_at IS NULL AND expires_at > CURRENT_TIMESTAMP"
        )
    ).scalar_one()
    if active:
        raise RuntimeError("Refusing downgrade: active Whop ownership authorizations exist")
    op.drop_index("ix_whop_saas_ownership_nonces_expires_at", table_name="whop_saas_ownership_nonces")
    op.drop_table("whop_saas_ownership_nonces")
