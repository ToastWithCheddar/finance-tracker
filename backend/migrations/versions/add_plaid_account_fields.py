"""Add Plaid account integration fields

Revision ID: add_plaid_account_fields
Revises: 93f7829207e8
Create Date: 2025-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_plaid_account_fields'
down_revision = '93f7829207e8'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Rename 'type' column to 'account_type' to avoid SQL keyword conflict
    op.alter_column('accounts', 'type', new_column_name='account_type')
    
    # Increase name column length
    op.alter_column('accounts', 'name', type_=sa.String(200))
    op.alter_column('accounts', 'account_type', type_=sa.String(50))
    
    # Add new Plaid integration fields
    op.add_column('accounts', sa.Column('plaid_access_token', sa.Text(), nullable=True))
    op.add_column('accounts', sa.Column('plaid_item_id', sa.String(100), nullable=True))
    
    # Add account metadata and sync status fields
    op.add_column('accounts', sa.Column('account_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('accounts', sa.Column('sync_status', sa.String(20), nullable=True, server_default='manual'))
    op.add_column('accounts', sa.Column('last_sync_error', sa.Text(), nullable=True))
    
    # Add connection health tracking fields
    op.add_column('accounts', sa.Column('connection_health', sa.String(20), nullable=True, server_default='unknown'))
    op.add_column('accounts', sa.Column('sync_frequency', sa.String(20), nullable=True, server_default='manual'))
    
    # Update existing records to have default values
    op.execute("UPDATE accounts SET sync_status = 'manual' WHERE sync_status IS NULL")
    op.execute("UPDATE accounts SET connection_health = 'not_connected' WHERE connection_health IS NULL")
    op.execute("UPDATE accounts SET sync_frequency = 'manual' WHERE sync_frequency IS NULL")
    
    # Make the new columns non-nullable after setting defaults
    op.alter_column('accounts', 'sync_status', nullable=False)
    op.alter_column('accounts', 'connection_health', nullable=False)
    op.alter_column('accounts', 'sync_frequency', nullable=False)

def downgrade() -> None:
    # Remove new columns
    op.drop_column('accounts', 'sync_frequency')
    op.drop_column('accounts', 'connection_health')
    op.drop_column('accounts', 'last_sync_error')
    op.drop_column('accounts', 'sync_status')
    op.drop_column('accounts', 'account_metadata')
    op.drop_column('accounts', 'plaid_item_id')
    op.drop_column('accounts', 'plaid_access_token')
    
    # Revert column changes
    op.alter_column('accounts', 'account_type', new_column_name='type')
    op.alter_column('accounts', 'name', type_=sa.String(100))
    op.alter_column('accounts', 'type', type_=sa.String(20))