"""Adds channel_message_id to experiences table

Revision ID: a2
Revises: a1
Create Date: 2025-09-25 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a2'
down_revision = 'a1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    try:
        op.add_column('experiences', sa.Column('channel_message_id', sa.BigInteger(), nullable=True))
    except Exception as e:
        print(f"Could not add column 'channel_message_id', it might already exist: {e}")


def downgrade() -> None:
    op.drop_column('experiences', 'channel_message_id')