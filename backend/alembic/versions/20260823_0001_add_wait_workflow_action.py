"""add WAIT workflow action enum value

Revision ID: 20260823_0001
Revises: 8c71245118ad
Create Date: 2026-08-23
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260823_0001"
down_revision: Union[str, None] = "8c71245118ad"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE workflow_action_type "
        "ADD VALUE IF NOT EXISTS 'WAIT'"
    )


def downgrade() -> None:
    # PostgreSQL enum-value removal requires enum recreation and can be
    # destructive once WAIT rows exist, so rollback is intentionally no-op.
    pass
