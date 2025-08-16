"""enable_row_level_security

Revision ID: e98b7b1df196
Revises: 9e561d011f4c
Create Date: 2025-08-12 16:56:48.917187

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e98b7b1df196'
down_revision: Union[str, None] = '9e561d011f4c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tables with user_id that need RLS
    tables_with_user_id = [
        'accounts', 'transactions', 'budgets', 'goals', 'insights',
        'recurring_transaction_rules', 'user_preferences'
    ]
    
    # Enable RLS for all user-owned tables
    for table in tables_with_user_id:
        # Enable RLS on the table
        op.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;')
        # Force RLS for the table owner (good security practice)
        op.execute(f'ALTER TABLE {table} FORCE ROW LEVEL SECURITY;')
        
        # Create RLS policy for user-owned data
        policy_sql = f"""
            CREATE POLICY user_access_policy ON {table}
            FOR ALL
            USING (user_id = current_setting('app.current_user_id')::uuid)
            WITH CHECK (user_id = current_setting('app.current_user_id')::uuid);
        """
        op.execute(policy_sql)
    
    # Special handling for categories table (system + user categories)
    op.execute('ALTER TABLE categories ENABLE ROW LEVEL SECURITY;')
    op.execute('ALTER TABLE categories FORCE ROW LEVEL SECURITY;')
    
    # Categories policy allows access to system categories (user_id IS NULL) + user's own categories
    categories_policy_sql = """
        CREATE POLICY user_and_system_access_policy ON categories
        FOR ALL
        USING (is_system IS TRUE OR user_id = current_setting('app.current_user_id')::uuid)
        WITH CHECK (user_id = current_setting('app.current_user_id')::uuid OR is_system IS TRUE);
    """
    op.execute(categories_policy_sql)


def downgrade() -> None:
    # Tables with user_id that had RLS enabled
    tables_with_user_id = [
        'accounts', 'transactions', 'budgets', 'goals', 'insights',
        'recurring_transaction_rules', 'user_preferences'
    ]
    
    # Remove RLS policies and disable RLS
    for table in tables_with_user_id:
        op.execute(f"DROP POLICY IF EXISTS user_access_policy ON {table};")
        op.execute(f'ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;')
    
    # Remove categories special policy
    op.execute("DROP POLICY IF EXISTS user_and_system_access_policy ON categories;")
    op.execute('ALTER TABLE categories DISABLE ROW LEVEL SECURITY;')
