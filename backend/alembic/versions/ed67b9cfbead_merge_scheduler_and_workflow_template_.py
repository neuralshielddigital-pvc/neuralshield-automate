"""merge scheduler and workflow template heads

Revision ID: ed67b9cfbead
Revises: 20260626_0001, 2e6ab80ac420
Create Date: 2026-07-12 07:53:12.812224

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ed67b9cfbead'
down_revision: Union[str, None] = ('20260626_0001', '2e6ab80ac420')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
