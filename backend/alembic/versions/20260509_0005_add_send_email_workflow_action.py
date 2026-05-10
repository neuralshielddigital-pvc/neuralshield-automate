"""add send email workflow action

Revision ID: 20260509_0005
Revises: 20260509_0004
Create Date: 2026-05-09 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260509_0005"
down_revision: str | None = "20260509_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            ALTER TYPE workflow_action_type ADD VALUE IF NOT EXISTS 'SEND_EMAIL';
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )


def downgrade() -> None:
    pass
