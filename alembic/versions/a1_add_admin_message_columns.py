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
    # --- START OF FIX ---
    # This block will change the user_id columns to BigInteger to support large IDs.
    # It is wrapped in a try-except block to prevent errors if the columns are already correct.
    try:
        op.alter_column('users', 'user_id',
                   existing_type=sa.INTEGER,
                   type_=sa.BigInteger(),
                   existing_nullable=False)
        print("Upgraded users.user_id to BigInteger.")
    except Exception as e:
        print(f"Could not alter users.user_id, it might already be BigInteger: {e}")

    try:
        op.alter_column('admins', 'user_id',
                   existing_type=sa.INTEGER,
                   type_=sa.BigInteger(),
                   existing_nullable=False)
        print("Upgraded admins.user_id to BigInteger.")
    except Exception as e:
        print(f"Could not alter admins.user_id, it might already be BigInteger: {e}")

    try:
        op.alter_column('experiences', 'user_id',
                   existing_type=sa.INTEGER,
                   type_=sa.BigInteger(),
                   existing_nullable=False)
        print("Upgraded experiences.user_id to BigInteger.")
    except Exception as e:
        print(f"Could not alter experiences.user_id, it might already be BigInteger: {e}")
    # --- END OF FIX ---

    # Original migration steps
    try:
        op.add_column('experiences', sa.Column('admin_message_id', sa.BigInteger(), nullable=True))
        op.add_column('experiences', sa.Column('admin_chat_id', sa.BigInteger(), nullable=True))
    except Exception as e:
        print(f"Could not add admin message columns, they might already exist: {e}")


def downgrade() -> None:
    op.drop_column('experiences', 'admin_chat_id')
    op.drop_column('experiences', 'admin_message_id')

    # Revert user_id columns back to Integer if needed
    op.alter_column('users', 'user_id',
               existing_type=sa.BigInteger(),
               type_=sa.INTEGER(),
               existing_nullable=False)
    op.alter_column('admins', 'user_id',
               existing_type=sa.BigInteger(),
               type_=sa.INTEGER(),
               existing_nullable=False)
    op.alter_column('experiences', 'user_id',
               existing_type=sa.BigInteger(),
               type_=sa.INTEGER(),
               existing_nullable=False)