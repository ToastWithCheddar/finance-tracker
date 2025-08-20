"""drop_recurring_transaction_rules_table

Revision ID: drop_recurring_transaction_rules
Revises: remove_audit_system
Create Date: 2025-08-19 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'drop_recurring_transaction_rules'
down_revision: Union[str, None] = 'remove_audit_system'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop the recurring_transaction_rules table and related objects"""
    # Drop foreign key constraints first if they exist
    op.execute("ALTER TABLE IF EXISTS recurring_transaction_rules DROP CONSTRAINT IF EXISTS recurring_transaction_rules_user_id_fkey")
    op.execute("ALTER TABLE IF EXISTS recurring_transaction_rules DROP CONSTRAINT IF EXISTS recurring_transaction_rules_account_id_fkey")
    op.execute("ALTER TABLE IF EXISTS recurring_transaction_rules DROP CONSTRAINT IF EXISTS recurring_transaction_rules_category_id_fkey")
    
    # Drop indices
    op.execute("DROP INDEX IF EXISTS idx_recurring_rule_user")
    op.execute("DROP INDEX IF EXISTS idx_recurring_rule_account")
    op.execute("DROP INDEX IF EXISTS idx_recurring_rule_active")
    op.execute("DROP INDEX IF EXISTS idx_recurring_rule_frequency")
    op.execute("DROP INDEX IF EXISTS idx_recurring_rule_next_due")
    
    # Drop the table
    op.drop_table('recurring_transaction_rules')
    
    # Drop the enum type used by frequency column
    op.execute("DROP TYPE IF EXISTS frequencytype")


def downgrade() -> None:
    """Recreate the recurring_transaction_rules table if needed for rollback"""
    # Recreate the enum type
    frequency_enum = sa.Enum('WEEKLY', 'BIWEEKLY', 'MONTHLY', 'QUARTERLY', 'ANNUALLY', 'CUSTOM', name='frequencytype')
    frequency_enum.create(op.get_bind())
    
    # Recreate the table
    op.create_table('recurring_transaction_rules',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('account_id', sa.UUID(), nullable=False),
        sa.Column('category_id', sa.UUID(), nullable=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('amount_cents', sa.BigInteger(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('frequency', frequency_enum, nullable=False),
        sa.Column('interval', sa.BigInteger(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('next_due_date', sa.Date(), nullable=False),
        sa.Column('last_generated_date', sa.Date(), nullable=True),
        sa.Column('tolerance_cents', sa.BigInteger(), nullable=False),
        sa.Column('auto_categorize', sa.Boolean(), nullable=False),
        sa.Column('generate_notifications', sa.Boolean(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_confirmed', sa.Boolean(), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('detection_method', sa.String(length=50), nullable=True),
        sa.Column('sample_transactions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('custom_rule', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notification_settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('rule_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('last_matched_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Recreate indices
    op.create_index('idx_recurring_rule_user', 'recurring_transaction_rules', ['user_id'], unique=False)
    op.create_index('idx_recurring_rule_account', 'recurring_transaction_rules', ['account_id'], unique=False)
    op.create_index('idx_recurring_rule_active', 'recurring_transaction_rules', ['is_active', 'is_confirmed'], unique=False)
    op.create_index('idx_recurring_rule_frequency', 'recurring_transaction_rules', ['frequency'], unique=False)
    op.create_index('idx_recurring_rule_next_due', 'recurring_transaction_rules', ['next_due_date'], unique=False)
    
    # Recreate foreign key constraints
    op.create_foreign_key('recurring_transaction_rules_user_id_fkey', 'recurring_transaction_rules', 'users', ['user_id'], ['id'])
    op.create_foreign_key('recurring_transaction_rules_account_id_fkey', 'recurring_transaction_rules', 'accounts', ['account_id'], ['id'])
    op.create_foreign_key('recurring_transaction_rules_category_id_fkey', 'recurring_transaction_rules', 'categories', ['category_id'], ['id'])