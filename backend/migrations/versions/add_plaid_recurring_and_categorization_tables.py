"""add_plaid_recurring_and_categorization_tables

Revision ID: bf8a9c4d7e12
Revises: 29aa6b4ed376
Create Date: 2025-08-16 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'bf8a9c4d7e12'
down_revision = '29aa6b4ed376'
branch_labels = None
depends_on = None


def upgrade():
    # Create plaid_recurring_transactions table
    op.create_table('plaid_recurring_transactions',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('plaid_recurring_transaction_id', sa.String(length=200), nullable=False),
    sa.Column('plaid_account_id', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('merchant_name', sa.String(length=200), nullable=True),
    sa.Column('amount_cents', sa.BigInteger(), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('plaid_frequency', sa.String(length=50), nullable=False),
    sa.Column('plaid_status', sa.String(length=50), nullable=False),
    sa.Column('plaid_category', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('last_amount_cents', sa.BigInteger(), nullable=True),
    sa.Column('last_date', sa.Date(), nullable=True),
    sa.Column('is_muted', sa.Boolean(), nullable=False),
    sa.Column('is_linked_to_rule', sa.Boolean(), nullable=False),
    sa.Column('linked_rule_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('first_detected_at', sa.DateTime(), nullable=False),
    sa.Column('last_sync_at', sa.DateTime(), nullable=False),
    sa.Column('sync_count', sa.BigInteger(), nullable=False),
    sa.Column('plaid_raw_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
    sa.ForeignKeyConstraint(['linked_rule_id'], ['recurring_transaction_rules.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('plaid_recurring_transaction_id')
    )
    
    # Create indexes for plaid_recurring_transactions
    op.create_index('idx_plaid_recurring_user', 'plaid_recurring_transactions', ['user_id'], unique=False)
    op.create_index('idx_plaid_recurring_account', 'plaid_recurring_transactions', ['account_id'], unique=False)
    op.create_index('idx_plaid_recurring_transaction_id', 'plaid_recurring_transactions', ['plaid_recurring_transaction_id'], unique=False)
    op.create_index('idx_plaid_recurring_sync', 'plaid_recurring_transactions', ['last_sync_at'], unique=False)
    op.create_index('idx_plaid_recurring_status', 'plaid_recurring_transactions', ['plaid_status', 'is_muted'], unique=False)
    op.create_index('idx_plaid_recurring_frequency', 'plaid_recurring_transactions', ['plaid_frequency'], unique=False)
    op.create_index('idx_plaid_recurring_linked', 'plaid_recurring_transactions', ['is_linked_to_rule', 'linked_rule_id'], unique=False)
    
    # Set default values
    op.alter_column('plaid_recurring_transactions', 'currency', server_default='USD')
    op.alter_column('plaid_recurring_transactions', 'is_muted', server_default=sa.text('false'))
    op.alter_column('plaid_recurring_transactions', 'is_linked_to_rule', server_default=sa.text('false'))
    op.alter_column('plaid_recurring_transactions', 'sync_count', server_default='1')

    # Create categorization_rule_templates table
    op.create_table('categorization_rule_templates',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('category', sa.String(length=100), nullable=False),
    sa.Column('conditions_template', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('actions_template', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('popularity_score', sa.BigInteger(), nullable=False),
    sa.Column('is_official', sa.Boolean(), nullable=False),
    sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('version', sa.String(length=20), nullable=False),
    sa.Column('parent_template_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('times_used', sa.BigInteger(), nullable=False),
    sa.Column('success_rating', sa.Float(), nullable=True),
    sa.Column('default_priority', sa.BigInteger(), nullable=False),
    sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for categorization_rule_templates
    op.create_index('idx_template_category', 'categorization_rule_templates', ['category'], unique=False)
    op.create_index('idx_template_official', 'categorization_rule_templates', ['is_official'], unique=False)
    op.create_index('idx_template_popularity', 'categorization_rule_templates', ['popularity_score', 'times_used'], unique=False)
    op.create_index('idx_template_created_by', 'categorization_rule_templates', ['created_by_user_id'], unique=False)
    op.create_index('idx_template_parent', 'categorization_rule_templates', ['parent_template_id'], unique=False)
    op.create_index('idx_template_tags', 'categorization_rule_templates', ['tags'], unique=False)
    
    # Set default values
    op.alter_column('categorization_rule_templates', 'popularity_score', server_default='0')
    op.alter_column('categorization_rule_templates', 'is_official', server_default=sa.text('false'))
    op.alter_column('categorization_rule_templates', 'version', server_default='1.0')
    op.alter_column('categorization_rule_templates', 'times_used', server_default='0')
    op.alter_column('categorization_rule_templates', 'default_priority', server_default='100')

    # Create categorization_rules table
    op.create_table('categorization_rules',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('priority', sa.BigInteger(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('conditions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('actions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('times_applied', sa.BigInteger(), nullable=False),
    sa.Column('last_applied_at', sa.DateTime(), nullable=True),
    sa.Column('success_rate', sa.Float(), nullable=True),
    sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('template_version', sa.String(length=20), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for categorization_rules
    op.create_index('idx_categorization_rule_user', 'categorization_rules', ['user_id'], unique=False)
    op.create_index('idx_categorization_rule_priority', 'categorization_rules', ['priority', 'is_active'], unique=False)
    op.create_index('idx_categorization_rule_performance', 'categorization_rules', ['times_applied', 'success_rate'], unique=False)
    op.create_index('idx_categorization_rule_template', 'categorization_rules', ['template_id'], unique=False)
    op.create_index('idx_categorization_rule_active', 'categorization_rules', ['is_active', 'user_id'], unique=False)
    
    # Set default values
    op.alter_column('categorization_rules', 'priority', server_default='100')
    op.alter_column('categorization_rules', 'is_active', server_default=sa.text('true'))
    op.alter_column('categorization_rules', 'times_applied', server_default='0')


def downgrade():
    # Drop categorization_rules table and indexes
    op.drop_index('idx_categorization_rule_active', table_name='categorization_rules')
    op.drop_index('idx_categorization_rule_template', table_name='categorization_rules')
    op.drop_index('idx_categorization_rule_performance', table_name='categorization_rules')
    op.drop_index('idx_categorization_rule_priority', table_name='categorization_rules')
    op.drop_index('idx_categorization_rule_user', table_name='categorization_rules')
    op.drop_table('categorization_rules')
    
    # Drop categorization_rule_templates table and indexes
    op.drop_index('idx_template_tags', table_name='categorization_rule_templates')
    op.drop_index('idx_template_parent', table_name='categorization_rule_templates')
    op.drop_index('idx_template_created_by', table_name='categorization_rule_templates')
    op.drop_index('idx_template_popularity', table_name='categorization_rule_templates')
    op.drop_index('idx_template_official', table_name='categorization_rule_templates')
    op.drop_index('idx_template_category', table_name='categorization_rule_templates')
    op.drop_table('categorization_rule_templates')
    
    # Drop plaid_recurring_transactions table and indexes
    op.drop_index('idx_plaid_recurring_linked', table_name='plaid_recurring_transactions')
    op.drop_index('idx_plaid_recurring_frequency', table_name='plaid_recurring_transactions')
    op.drop_index('idx_plaid_recurring_status', table_name='plaid_recurring_transactions')
    op.drop_index('idx_plaid_recurring_sync', table_name='plaid_recurring_transactions')
    op.drop_index('idx_plaid_recurring_transaction_id', table_name='plaid_recurring_transactions')
    op.drop_index('idx_plaid_recurring_account', table_name='plaid_recurring_transactions')
    op.drop_index('idx_plaid_recurring_user', table_name='plaid_recurring_transactions')
    op.drop_table('plaid_recurring_transactions')