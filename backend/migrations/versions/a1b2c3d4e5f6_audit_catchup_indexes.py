"""audit catchup indexes

Revision ID: a1b2c3d4e5f6
Revises: 0ebba5935295
Create Date: 2026-04-27 00:00:00.000000

Adds the missing indexes flagged by the production-hardening audit:

- BE-PERF-003: GIN index on ``transactions.tags`` (text[]) so tag containment
  queries (``tags @> ARRAY['foo']``) are servable.
- BE-PERF-004: composite btree on ``transactions(user_id, status, transaction_date)``
  to support the very common "filter by user + status, order by date" access
  pattern used in transaction listing and dashboard summary queries.

Notes / scope decision (per docs/audit/improvement-sections/A-performance.md):

* This revision is intentionally **index-only**. The model layer has drifted
  from ``0ebba5935295`` in places that go beyond indexes (some columns, some
  enum values, and a few tables created at runtime via
  ``Base.metadata.create_all`` in ``app/main.py``). Authoring a full table-level
  catchup safely requires the database to be reachable for autogenerate, which
  is not the case in this environment. The catchup-tables work is therefore
  TODO and tracked under findings BE-PR-001 / BE-PR-002.
* For Postgres in production, the ideal form for these indexes is
  ``CREATE INDEX CONCURRENTLY``. Alembic by default wraps each migration in a
  transaction, which is incompatible with ``CONCURRENTLY``. To use it, the
  migration must opt out of the transaction with
  ``with op.get_context().autocommit_block():``. Left as a follow-up; the
  ``IF NOT EXISTS`` form below is idempotent and re-runnable.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "0ebba5935295"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # BE-PERF-003: GIN index on transactions.tags (text[]) for containment queries.
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_transaction_tags_gin "
        "ON transactions USING GIN (tags)"
    )

    # BE-PERF-004: composite btree to back (user_id, status, transaction_date)
    # filter+order queries used by /api/transactions and dashboard endpoints.
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_transaction_user_status_date "
        "ON transactions (user_id, status, transaction_date)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_transaction_user_status_date")
    op.execute("DROP INDEX IF EXISTS idx_transaction_tags_gin")
