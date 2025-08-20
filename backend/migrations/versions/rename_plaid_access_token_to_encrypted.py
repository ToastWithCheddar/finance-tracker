"""rename plaid_access_token to encrypted

Revision ID: encrypt_plaid_tokens_001
Revises: add_plaid_account_fields
Create Date: 2025-01-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'encrypt_plaid_tokens_001'
down_revision = 'add_plaid_account_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Rename plaid_access_token to plaid_access_token_encrypted.
    Existing tokens will need to be re-encrypted when the encryption service is enabled.
    """
    # Rename the column from plaid_access_token to plaid_access_token_encrypted
    op.alter_column('accounts', 'plaid_access_token', 
                   new_column_name='plaid_access_token_encrypted')


def downgrade() -> None:
    """
    Rename plaid_access_token_encrypted back to plaid_access_token.
    """
    # Rename the column back to plaid_access_token
    op.alter_column('accounts', 'plaid_access_token_encrypted', 
                   new_column_name='plaid_access_token')