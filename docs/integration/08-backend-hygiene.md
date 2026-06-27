# 08 — Backend hygiene + concurrency cleanup (Day 21)

## Summary

First day of the Phase-2 closeout extending the recorded scope from ~22 to ~25
days. Closes six backend findings flagged in `docs/audit/findings.csv` and
documents a follow-up plan for the only remaining honest backend gap
(BE-PERF-002).

## Files deleted

| Path | Reason |
|---|---|
| `backend/app/seed_data.py` | Duplicate of `backend/app/scripts/seed_data.py`. Only consumer was `database_manager.py` (also deleted). Closes **BE-PR-003**. |
| `backend/app/database_manager.py` | Wrapped `app.database` plus the duplicate seed module without adding value. No external imports. Closes **BE-PR-004**. |

## Files added

| Path | Purpose |
|---|---|
| `backend/migrations/versions/b2c3d4e5f6a7_functional_abs_amount_cents_index.py` | Functional btree index `idx_transaction_abs_amount_cents` on `abs(amount_cents)`; idempotent (`IF NOT EXISTS`). Closes **BE-PERF-008**. |

## Files edited

| Path:line | Change |
|---|---|
| `backend/app/websocket/manager.py:203-254` | `send_full_sync` now opens its session with `with get_db_session() as db:` so the session closes on early return / exception. Eliminates DB session leak. Closes **BE-WS-001**. |
| `backend/app/websocket/manager.py:397-405` | Shutdown loop logs each per-socket close failure (`logger.warning`) instead of silently swallowing it. Closes **BE-WS-002**. |
| `scripts/check.sh` | Drops `\|\| true` on lint/test invocations; adds `set -euo pipefail`; rewritten to surface failures and exit non-zero. Closes **INFRA-CI-002**. |

## BE-PERF-002 follow-up plan (documented, not closed)

Migrating from `psycopg2` (sync) to `asyncpg` (async) under FastAPI is **out
of the 25-day envelope** because it touches every service module
(`backend/app/services/*.py`), the test fixtures
(`backend/tests/conftest.py`), and the alembic config. Recommended next
phase:

1. Introduce an `async_engine` / `async_session_maker` alongside the existing
   sync engine (no removal yet) — additive, ~0.5d.
2. Migrate one service at a time, gated by a feature flag, with side-by-side
   integration tests. Order: read-heavy services first (analytics, dashboard,
   ml) to validate plumbing, then mutating ones (transactions, sync) — ~3d.
3. Switch alembic to `async` engine; remove the sync engine — ~0.5d.

Total: ~4 days. Tracked but **deliberately not started** during the 25-day
phase to avoid mid-flight database driver swaps under production traffic.

## Verification

- `python -m py_compile backend/app/websocket/manager.py` — clean.
- `grep -rn "from app.seed_data\\|app.database_manager\\|database_manager" backend/ --include='*.py' | grep -v __pycache__` — empty.
- `grep -rn "next(get_db())" backend/app/websocket/` — empty (was 1 hit before).
- `python -c "import yaml" 2>/dev/null` — n/a, this wave is Python-only.
- `bash -n scripts/check.sh` — parses; `set -euo pipefail` in place.
- New migration: `alembic upgrade head` against a fresh DB applies
  `b2c3d4e5f6a7` after `a1b2c3d4e5f6`.

## Open follow-ups

- BE-PERF-002 — psycopg2→asyncpg migration documented above; not started.
