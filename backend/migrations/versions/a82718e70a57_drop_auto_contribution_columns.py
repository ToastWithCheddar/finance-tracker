"""drop_auto_contribution_columns

Revision ID: a82718e70a57
Revises: b09be3ac014c
Create Date: 2025-08-21 11:43:00.042555

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a82718e70a57'
down_revision: Union[str, None] = 'b09be3ac014c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop auto-contribution columns from goals table
    op.drop_column('goals', 'auto_contribute')
    op.drop_column('goals', 'auto_contribution_amount_cents')
    op.drop_column('goals', 'auto_contribution_source')


def downgrade() -> None:
    # Re-add auto-contribution columns to goals table
    op.add_column('goals', sa.Column('auto_contribute', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('goals', sa.Column('auto_contribution_amount_cents', sa.BigInteger(), nullable=True))
    op.add_column('goals', sa.Column('auto_contribution_source', sa.String(100), nullable=True))
