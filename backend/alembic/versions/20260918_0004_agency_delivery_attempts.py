"""Track bounded Agency delivery attempts and SMTP submission separately."""
from alembic import op
import sqlalchemy as sa

revision = '20260918_0004'
down_revision = '20260831_0003'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('agency_fulfilments', sa.Column('attempt_count', sa.Integer(), server_default='0', nullable=False))
    for name in ('next_attempt_at', 'claimed_at', 'email_submitted_at'):
        op.add_column('agency_fulfilments', sa.Column(name, sa.DateTime(timezone=True), nullable=True))


def downgrade():
    for name in ('email_submitted_at', 'claimed_at', 'next_attempt_at', 'attempt_count'):
        op.drop_column('agency_fulfilments', name)
