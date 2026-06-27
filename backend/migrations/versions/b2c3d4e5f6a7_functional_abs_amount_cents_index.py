"""functional abs(amount_cents) index for transactions

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-29 00:00:00.000000

Closes BE-PERF-008. Several reporting and dashboard queries filter on
``abs(amount_cents)`` (e.g., "transactions over $X regardless of sign").
Without a functional index, Postgres has to seq-scan or apply the
expression on every row. This adds a btree index on the expression
itself.

Idempotent (``IF NOT EXISTS``) so it can be re-run on environments where
the catchup migration was already applied.
"""

from alembic import op


revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_transaction_abs_amount_cents "
        "ON transactions (abs(amount_cents))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_transaction_abs_amount_cents")
