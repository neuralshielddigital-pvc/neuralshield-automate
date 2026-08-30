"""add Agency member access tokens

Revision ID: 20260831_0003
Revises: 20260831_0002
Create Date: 2026-08-31
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260831_0003"
down_revision: Union[str, None] = "20260831_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agency_member_access_tokens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "token_hash",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "used_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "revoked_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["agency_customers.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )

    for column in (
        "customer_id",
        "token_hash",
        "expires_at",
    ):
        op.create_index(
            op.f(
                f"ix_agency_member_access_tokens_{column}"
            ),
            "agency_member_access_tokens",
            [column],
            unique=False,
        )


def downgrade() -> None:
    for column in (
        "expires_at",
        "token_hash",
        "customer_id",
    ):
        op.drop_index(
            op.f(
                f"ix_agency_member_access_tokens_{column}"
            ),
            table_name="agency_member_access_tokens",
        )

    op.drop_table("agency_member_access_tokens")
