"""Adds admin_message_id and admin_chat_id to experiences table

Revision ID: a1
Revises: 
Create Date: 2025-09-25 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if columns exist before adding them to prevent errors on restart
    try:
        op.add_column('experiences', sa.Column('admin_message_id', sa.BigInteger(), nullable=True))
        op.add_column('experiences', sa.Column('admin_chat_id', sa.BigInteger(), nullable=True))
    except Exception as e:
        print(f"Could not add columns, they might already exist: {e}")


def downgrade() -> None:
    op.drop_column('experiences', 'admin_chat_id')
    op.drop_column('experiences', 'admin_message_id')