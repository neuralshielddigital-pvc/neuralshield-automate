"""add tenant slug

Revision ID: 20260510_0008
Revises: 86b7e508a82b
Create Date: 2026-05-10 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260510_0008"
down_revision: str | None = "86b7e508a82b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("slug", sa.String(length=160), nullable=True))
    op.execute(
        """
        UPDATE tenants
        SET slug = COALESCE(
            NULLIF(regexp_replace(lower(name), '[^a-z0-9]+', '', 'g'), ''),
            'tenant'
        )
        WHERE slug IS NULL
        """
    )
    op.alter_column("tenants", "slug", nullable=False)
    op.create_index(op.f("ix_tenants_slug"), "tenants", ["slug"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_tenants_slug"), table_name="tenants")
    op.drop_column("tenants", "slug")
