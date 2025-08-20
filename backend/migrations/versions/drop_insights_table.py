"""drop insights table

Revision ID: drop_insights_table
Revises: add_budget_alert_settings
Create Date: 2025-08-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'drop_insights_table'
down_revision = 'add_budget_alert_settings'
branch_labels = None
depends_on = None


def upgrade():
    """Drop the insights table and related indices"""
    # Drop foreign key constraints first if they exist
    op.execute("ALTER TABLE IF EXISTS insights DROP CONSTRAINT IF EXISTS insights_user_id_fkey")
    op.execute("ALTER TABLE IF EXISTS insights DROP CONSTRAINT IF EXISTS insights_transaction_id_fkey")
    
    # Drop indices
    op.execute("DROP INDEX IF EXISTS ix_insights_user_id")
    op.execute("DROP INDEX IF EXISTS ix_insights_type")
    op.execute("DROP INDEX IF EXISTS ix_insights_priority")
    op.execute("DROP INDEX IF EXISTS ix_insights_is_read")
    op.execute("DROP INDEX IF EXISTS ix_insights_created_at")
    
    # Drop the insights table
    op.drop_table('insights')


def downgrade():
    """Recreate the insights table if needed for rollback"""
    op.create_table('insights',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False, default=False),
        sa.Column('extra_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Recreate indices
    op.create_index('ix_insights_user_id', 'insights', ['user_id'])
    op.create_index('ix_insights_type', 'insights', ['type'])
    op.create_index('ix_insights_priority', 'insights', ['priority'])
    op.create_index('ix_insights_is_read', 'insights', ['is_read'])
    op.create_index('ix_insights_created_at', 'insights', ['created_at'])
    
    # Recreate foreign key constraints
    op.create_foreign_key('insights_user_id_fkey', 'insights', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('insights_transaction_id_fkey', 'insights', 'transactions', ['transaction_id'], ['id'], ondelete='SET NULL')