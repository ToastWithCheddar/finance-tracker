# `backend/tests/` — Backend test suite

Foundation wave. This is the working **skeleton** the rest of Section B will build on.
It deliberately does **not** modify `backend/tests/` (the bit-rotted internship
suite — see findings BE-TEST-001..004). The internship suite stays in place;
the audit suite stands alongside it with its own venv, its own pins, and a
real Postgres + Redis via testcontainers.

## What's in this wave

| Path | Purpose |
|---|---|
| `pyproject.toml` | Pinned tooling. Separate venv from `backend/`. |
| `conftest.py` | Session-scoped Postgres 15 + Redis 7 testcontainers. App dep overrides. Supabase respx mock. |
| `factories/` | factory-boy SQLAlchemy factories for User, Account, Transaction, Category, Budget. |
| `helpers/supabase_mock.py` | respx routes for `https://stub.supabase.co/auth/v1/*`. |
| `helpers/auth_client.py` | `make_authenticated_client(user)` returning an httpx `TestClient`. |
| `integration/test_health.py` | `/health` and `/health?detailed=true`. |
| `integration/test_auth_router.py` | full register → login → /me → refresh → logout (replaces broken `backend/tests/integration/test_auth_router.py`). |
| `integration/test_transactions_router.py` | POST/GET/DELETE against real Postgres so JSONB/ARRAY/enum work. |
| `security/test_dev_bypass_disabled_in_prod.py` | proves BE-SEC-002 is exploitable today and will pass once the fix lands. |

Future waves expand `unit/`, `contract/`, `concurrency/`, the rest of `security/`, and the
remaining router integration tests listed in `docs/audit/improvement-sections/B-testing.md`.

## Wave 4 additions — security / concurrency / contract

These suites prove specific findings from `docs/audit/findings.csv`. All
tests use `pytest.mark.xfail(strict=False, reason="<finding-id>")` where the
finding is still open, so the suite goes green today and flips to "unexpected
pass" the moment the fix lands.

### `security/`

| File | Finding | One-liner |
|---|---|---|
| `test_dev_bypass_disabled_in_prod.py` | BE-SEC-002 | `dev-mock-token-*` must NOT grant access in production/staging. |
| `test_rls_cross_user_leak.py` | BE-SEC-001 | User A authed via `/api/transactions` cannot see User B rows. |
| `test_rate_limits.py` | BE-RL-001 | `/auth/login` and `/auth/register` must produce 429 under burst. |
| `test_admin_ws_guards.py` | BE-SEC-007 | `/ws/stats`, `/ws/broadcast`, `/ws/test-message` must require admin. |
| `test_export_dos.py` | BE-SEC-009 | `/transactions/export` must cap rows or rate-limit huge ranges/bursts. |
| `test_encryption_roundtrip.py` | BE-SEC-003 | Hypothesis: `decrypt(encrypt(x)) == x`; encrypt/decrypt must RAISE on error, never return plaintext. |

### `concurrency/`

| File | Finding | One-liner |
|---|---|---|
| `test_user_provisioning_toctou.py` | BE-CONC-001 | Two concurrent first-login `/api/auth/me` requests for one Supabase user must yield exactly one DB row. |
| `test_sync_lock_fence.py` | BE-CONC-002 | Worker B must NOT be able to release worker A's `TransactionSyncService` lock without the matching fence token. |

### `contract/`

| File | Finding | One-liner |
|---|---|---|
| `test_plaid_link_token.py` | BE-SEC-006 (defence-in-depth) | Pin POST `/link/token/create` body shape: `client_id`, `secret`, `client_name`, `country_codes`, `language`, `user.client_user_id`. |
| `test_supabase_get_user.py` | BE-SEC-008 (contract pin) | Pin `auth/v1/user` response shape used by the JWT extraction path in `_validate_supabase_token` → `_provision_user_from_supabase`. |

Fixtures live under `contract/fixtures/{plaid,supabase}/*.json` so they can be
diffed against real Plaid/Supabase responses captured from the wire.

## Running locally

```bash
cd backend
python3.11 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest tests -x -v
```

The second `pip install -e ../../../backend` is the gotcha: this suite imports
the application under test as `from app.main import app`, so the
`finance-tracker/backend/` directory must be on `sys.path`. We do NOT vendor
or patch backend code — we just let the audit venv see it.

### Requirements
- Docker daemon running (testcontainers spins real `postgres:15-alpine` and
  `redis:7-alpine` containers per session).
- Python 3.11.

If Docker is unavailable, every test in this suite is expected to **error** at
fixture setup, not silently fall through to SQLite — that is the whole point
of moving away from `backend/tests/conftest.py`.

## Conventions

- Money in cents (`amount_cents: BigInteger`). Never floats.
- Postgres enums are uppercase (`BudgetPeriod.MONTHLY` stored as `"MONTHLY"`).
- Supabase HTTP is **always** mocked via respx pointed at `https://stub.supabase.co`.
  No live network calls. If a test hits a live Supabase, it's a bug in the test.
- factory-boy factories use `SQLAlchemyModelFactory` with `sqlalchemy_session_persistence = "commit"`.
- Per-test isolation via a SAVEPOINT-rolled-back session (the Postgres container
  itself is reused across the whole session for speed).
