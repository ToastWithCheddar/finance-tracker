"""Migrate low_balance_threshold to cents

Revision ID: 29aa6b4ed376
Revises: 4c48d9ea50e0
Create Date: 2025-08-15 09:04:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '29aa6b4ed376'
down_revision: Union[str, None] = '4c48d9ea50e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Fix timeline annotations index first
    op.drop_index('ix_timeline_annotations_date_desc', table_name='timeline_annotations')
    op.create_index('ix_timeline_annotations_date_desc', 'timeline_annotations', ['date'], unique=False, postgresql_ops={'date': 'DESC'})
    
    # Add the new column with nullable=True first
    op.add_column('user_preferences', sa.Column('low_balance_threshold_cents', sa.Integer(), nullable=True))
    
    # Migrate existing data: convert dollars to cents
    op.execute(
        "UPDATE user_preferences SET low_balance_threshold_cents = ROUND(low_balance_threshold * 100) WHERE low_balance_threshold IS NOT NULL"
    )
    
    # Set default value for any NULL values (should be 10000 cents = $100)
    op.execute(
        "UPDATE user_preferences SET low_balance_threshold_cents = 10000 WHERE low_balance_threshold_cents IS NULL"
    )
    
    # Now make the column NOT NULL
    op.alter_column('user_preferences', 'low_balance_threshold_cents', nullable=False)
    
    # Drop the old column
    op.drop_column('user_preferences', 'low_balance_threshold')


def downgrade() -> None:
    # Add back the old column
    op.add_column('user_preferences', sa.Column('low_balance_threshold', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True))
    
    # Migrate data back: convert cents to dollars
    op.execute(
        "UPDATE user_preferences SET low_balance_threshold = low_balance_threshold_cents / 100.0 WHERE low_balance_threshold_cents IS NOT NULL"
    )
    
    # Set default for any NULL values
    op.execute(
        "UPDATE user_preferences SET low_balance_threshold = 100.0 WHERE low_balance_threshold IS NULL"
    )
    
    # Make the old column NOT NULL
    op.alter_column('user_preferences', 'low_balance_threshold', nullable=False)
    
    # Drop the new column
    op.drop_column('user_preferences', 'low_balance_threshold_cents')
    
    # Revert timeline annotations index
    op.drop_index('ix_timeline_annotations_date_desc', table_name='timeline_annotations', postgresql_ops={'date': 'DESC'})
    op.create_index('ix_timeline_annotations_date_desc', 'timeline_annotations', [sa.text('date DESC')], unique=False)