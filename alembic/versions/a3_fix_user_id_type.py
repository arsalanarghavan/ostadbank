"""Fix user_id columns to use BigInteger across all relevant tables.

Revision ID: a3
Revises: a2
Create Date: 2025-09-26 00:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a3'
down_revision = 'a2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    print("--- Running migration a3: Changing user_id columns to BigInteger ---")
    
    # List of tables and columns to update
    tables_to_update = ['users', 'admins', 'experiences']
    
    for table in tables_to_update:
        try:
            op.alter_column(
                table, 
                'user_id',
                existing_type=sa.INTEGER,
                type_=sa.BigInteger(),
                existing_nullable=False
            )
            print(f"Successfully altered '{table}.user_id' to BigInteger.")
        except Exception as e:
            # This handles cases where the column might already be BigInteger
            print(f"Could not alter '{table}.user_id'. It might already be the correct type. Error: {e}")
            
    print("--- Finished migration a3 ---")


def downgrade() -> None:
    print("--- Downgrading migration a3: Reverting user_id columns to Integer ---")
    
    tables_to_update = ['users', 'admins', 'experiences']
    
    for table in tables_to_update:
        try:
            op.alter_column(
                table, 
                'user_id',
                existing_type=sa.BigInteger(),
                type_=sa.INTEGER(),
                existing_nullable=False
            )
            print(f"Successfully reverted '{table}.user_id' to Integer.")
        except Exception as e:
            print(f"Could not downgrade '{table}.user_id'. Error: {e}")
            
    print("--- Finished downgrade of a3 ---")