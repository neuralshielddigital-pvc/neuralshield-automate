"""add user stripe customer id

Revision ID: 20260507_0002
Revises: 20260505_0001
Create Date: 2026-05-07 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260507_0002"
down_revision: str | None = "20260505_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("stripe_customer_id", sa.String(length=255), nullable=True))
    op.create_index(op.f("ix_users_stripe_customer_id"), "users", ["stripe_customer_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_stripe_customer_id"), table_name="users")
    op.drop_column("users", "stripe_customer_id")
