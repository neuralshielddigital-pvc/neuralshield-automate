"""allow Agency customer creation from Paddle customer ID before enrichment

Revision ID: 20260831_0002
Revises: 20260831_0001
Create Date: 2026-08-31
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260831_0002"
down_revision: Union[str, None] = "20260831_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "agency_customers",
        "email",
        existing_type=sa.String(length=320),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "agency_customers",
        "email",
        existing_type=sa.String(length=320),
        nullable=False,
    )
