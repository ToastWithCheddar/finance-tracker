"""create_user_sessions_table

Revision ID: 94609d563151
Revises: 3adf66499bc9
Create Date: 2025-08-14 19:22:39.187947

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '94609d563151'
down_revision: Union[str, None] = '3adf66499bc9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Import required types
    from sqlalchemy.dialects.postgresql import UUID, JSONB
    
    # Create user_sessions table
    op.create_table('user_sessions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('session_token', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('device_info', sa.String(255), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),  # IPv6 max length
        sa.Column('location', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('last_activity', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # Create indexes for user_sessions
    op.create_index('idx_user_sessions_user_id', 'user_sessions', ['user_id'])
    op.create_index('idx_user_sessions_token', 'user_sessions', ['session_token'])
    op.create_index('idx_user_sessions_active', 'user_sessions', ['user_id', 'is_active'])
    op.create_index('idx_user_sessions_last_activity', 'user_sessions', ['last_activity'])


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('idx_user_sessions_last_activity', table_name='user_sessions')
    op.drop_index('idx_user_sessions_active', table_name='user_sessions') 
    op.drop_index('idx_user_sessions_token', table_name='user_sessions')
    op.drop_index('idx_user_sessions_user_id', table_name='user_sessions')
    
    # Drop the table
    op.drop_table('user_sessions')
