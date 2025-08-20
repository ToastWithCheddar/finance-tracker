"""drop_timeline_annotations_table

Revision ID: drop_timeline_annotations
Revises: add_plaid_recurring_and_categorization_tables
Create Date: 2025-08-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'drop_timeline_annotations'
down_revision: Union[str, None] = 'add_plaid_recurring_and_categorization_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop the timeline_annotations table and its related indexes"""
    # Drop indexes first
    op.drop_index('ix_timeline_annotations_user_date', table_name='timeline_annotations')
    op.drop_index('ix_timeline_annotations_date_desc', table_name='timeline_annotations')
    op.drop_index('ix_timeline_annotations_user_id', table_name='timeline_annotations')
    
    # Drop the table
    op.drop_table('timeline_annotations')


def downgrade() -> None:
    """Recreate the timeline_annotations table and its indexes"""
    # Recreate table
    op.create_table('timeline_annotations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('date', sa.DATE(), nullable=False),
        sa.Column('title', sa.VARCHAR(length=200), nullable=False),
        sa.Column('description', sa.TEXT(), nullable=True),
        sa.Column('icon', sa.VARCHAR(length=50), nullable=True),
        sa.Column('color', sa.VARCHAR(length=20), nullable=True),
        sa.Column('extra_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Recreate indexes
    op.create_index('ix_timeline_annotations_user_id', 'timeline_annotations', ['user_id'], unique=False)
    op.create_index('ix_timeline_annotations_date_desc', 'timeline_annotations', ['date'], unique=False, postgresql_ops={'date': 'DESC'})
    op.create_index('ix_timeline_annotations_user_date', 'timeline_annotations', ['user_id', 'date'], unique=False)