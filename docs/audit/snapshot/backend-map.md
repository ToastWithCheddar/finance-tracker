# Backend snapshot — `backend/`

FastAPI 0.104+, SQLAlchemy 2.0 ORM (typed `Mapped[]`), Pydantic v2, Postgres via psycopg2 (sync), Redis (asyncio), Supabase Auth, Plaid SDK, Celery client. ~17.9k LOC of `app/`, ~4.2k LOC of `tests/` (mostly bit-rotted — see findings).

## Module tree

```
backend/
├── app/
│   ├── main.py                 # 557 LOC: factory, middleware, lifespan, exception handlers
│   ├── config.py               # 235 LOC: Settings(BaseSettings), partly redundant with os.getenv
│   ├── database.py             # SQLAlchemy engine + session (pool_size=20, max_overflow=30)
│   ├── database_manager.py     # Parallel abstraction; canonical-vs-not unclear
│   ├── dependencies.py         # DI providers, ownership guards
│   ├── seed_data.py            # duplicated with scripts/seed_data.py
│   ├── auth/
│   │   ├── auth_service.py     # 278 LOC: register/login/refresh delegates to Supabase
│   │   ├── dependencies.py     # 339 LOC: get_current_user, RLS hook (broken), webhook verify
│   │   └── supabase_client.py  # supabase-py wrapper
│   ├── core/
│   │   ├── exceptions.py       # FinanceTrackerException tree
│   │   └── redis_client.py     # 244 LOC, asyncio
│   ├── websocket/
│   │   ├── manager.py          # 408 LOC: per-user subscriber tasks, Redis fanout
│   │   ├── events.py
│   │   └── schemas.py
│   ├── services/               # 22 service files; orchestration-heavy
│   │   ├── transaction_service.py        (815)
│   │   ├── transaction_sync_service.py   (940)
│   │   ├── budget_service.py             (945)
│   │   ├── goal_service.py               (610)
│   │   ├── ml_service.py                 (649) — httpx async client to ml-worker
│   │   ├── plaid_account_service.py      (490)
│   │   ├── plaid_transaction_service.py
│   │   ├── plaid_orchestration_service.py
│   │   ├── reconciliation_service.py     (882)
│   │   ├── notification_service.py       (472)
│   │   ├── monitoring_service.py         (231) — exists, never wired
│   │   ├── financial_health_service.py
│   │   ├── encryption_service.py         — fail-soft! Plaid token risk
│   │   └── ...
│   ├── models/                 # 11 SQLAlchemy models + base
│   ├── schemas/                # Pydantic v2 schemas
│   ├── routes/                 # 16 routers
│   ├── utils/                  # validators, security
│   └── scripts/                # init_db, seed_data
├── migrations/                 # ONE Alembic revision — drift unmanaged
├── tests/                      # bit-rotted (see findings)
├── Dockerfile
├── alembic.ini
├── init.sql
├── pyproject.toml              # pytest, black, isort, mypy config
├── requirements*.txt
└── .pre-commit-config.yaml
```

## Routers and endpoints

Mounted from `app/main.py:345-508`.

### `/health` (`routes/health.py`)
- `GET /health` — `?detailed=true` checks DB, Redis ping, Supabase configured flag.

### `/api/auth` (`routes/auth.py`)
- `GET /me`, `POST /register`, `POST /login`, `POST /logout` 204, `POST /refresh`, `POST /request-password-reset`, `POST /resend-verification`, `POST /change-password`, `GET /health`.

### `/api/users` (`routes/users.py`)
- `GET/PUT/DELETE /me`, `GET /search`, `GET /{user_id}`, `GET /me/profile`, `GET/POST/DELETE /me/sessions[/...]`, `GET /me/sessions/stats`.

### `/api/categories` (`routes/categories.py`)
- `GET /`, `GET /system`, `GET /my`, `GET /hierarchy`, `GET /{id}`, `POST /`, `PUT /{id}`, `DELETE /{id}`.

### `/api/transactions` (`routes/transactions.py`, 589 LOC)
- `POST ""`, `GET /histogram`, `GET /export` (csv/json — unbounded), `GET/PUT/DELETE /{id}`, `GET ""` (paginated), `POST /import` (CSV), `POST /bulk-delete`, `GET /search_transactions`, `GET /categories`.

### `/api/budgets` (`routes/budget.py`)
- CRUD + `GET /{id}/progress`, `GET /analytics/summary`, `GET /analytics/alerts`, `GET /{id}/calendar`.

### `/api/goals` (`routes/goals.py`)
- CRUD + `GET /goals/stats`, `POST /goals/{id}/contributions`, `GET /goals/{id}/contributions`, `GET /goals/types/options`.

### `/api/dashboard` (`routes/dashboard.py`)
- `GET /`, `GET /category-breakdown`, `GET /net-worth-trend`, `GET /summary`. Sequential `count()` queries per request — caching opportunity.

### `/api/accounts` (split across 4 files)
- `accounts_basic.py` — CRUD + `/{id}/with-transactions`.
- `accounts_plaid.py` — `/plaid/link-token`, `/plaid/exchange-token`, `/connection-status`, `/plaid/update-mode`, `/plaid/disconnect`.
- `accounts_sync.py` — `/sync-balances`, `/sync-transactions`, `/sync-overview`, `/{id}/sync-status`.
- `accounts_reconciliation.py` — `/{id}/reconcile`, `/reconcile-all`, `/{id}/reconciliation-entry`, `/{id}/reconciliation-history`, `/{id}/health`.

### `/api/webhooks` (`routes/webhooks.py`)
- `POST /supabase` (HMAC bearer secret), `POST /plaid` (broken — `PLAID_BASE_URL` undefined).

### `/api/ml` (`routes/ml.py`)
- `POST /categorize` — **blocks event loop** with `result_async.get(timeout=30)`.
- `GET /health`, `GET /stats`, `POST /batch-categorize`, `POST /add-example` 201, `POST /export-model`, `GET /performance`.

### `/api/notifications` (`routes/notifications.py`)
- `GET /`, `GET /stats`, `PATCH /{id}`, `DELETE /{id}`, `POST /mark-all-read`, `GET /{id}`.

### WebSockets (`routes/websockets.py`)
- `WS /ws`, `GET /ws/health`, `GET /ws/stats`, `POST /ws/test-message/{user_id}`, `POST /ws/broadcast`. Last three documented as admin but only require regular auth → privilege escalation.

## Data layer

`BaseModel` (`models/base.py:17-45`): UUID PK (`uuid4`), `created_at`/`updated_at` server-default now.

Models: `User`, `Account`, `Transaction`, `Category`, `Budget`, `Goal`, `GoalContribution`, `GoalMilestone`, `Notification`, `BudgetAlertSettings`, `UserSession`, `MLModel`.

Money in cents (`BigInteger`). Postgres enums for `BudgetPeriod`, `GoalStatus/Type/Priority`, `NotificationType`. JSONB on `Transaction.location`, `Transaction.metadata_json`, `Notification.notification_metadata`. ARRAY for `Transaction.tags`.

Indexes (selected highlights):
- `idx_transaction_user_date`, `idx_transaction_account_date`, `idx_transaction_category`, `idx_transaction_merchant`, `idx_transaction_amount`, `idx_transaction_status`, `idx_transaction_plaid_id`.
- `idx_account_user_active`, `idx_account_type_active`, `idx_account_plaid_id`, `idx_account_sync_status`.
- **Missing:** GIN on `tags`, composite `(user_id, status, transaction_date)`, functional index on `func.abs(amount_cents)`.

Connection pool (`database.py:21-32`): `pool_size=20, max_overflow=30, pool_pre_ping=True, pool_recycle=3600`. **Sync psycopg2 under FastAPI async** — every DB call blocks the event loop.

## Auth

Supabase-hosted JWT; no local password storage. `AuthService` delegates to `supabase.client.auth.*`. JWT validation in `auth/dependencies.py:124-159`:
1. Dev-mock-token short-circuit (`:74-101`) — gated only on `ENVIRONMENT == "development"`.
2. `supabase.client.auth.get_user(token)` — sync HTTP inside async handler (blocks loop, `:105`).
3. Auto-provisions local `users` row on first login (TOCTOU-prone, `:32-72`).

RLS hook `user_context_db` (`:213-231`): runs `SET LOCAL app.current_user_id = :user_id`. The `with` block exits before the session is consumed → effectively a no-op.

## Real-time

`RedisWebSocketManager` (`websocket/manager.py`):
- In-memory `connections: Dict[str, Set[WebSocket]]`.
- One asyncio Redis subscriber task per user.
- Cross-instance fanout via Redis pub/sub `ws:user:{user_id}`.
- `get_db()` leaked in `send_full_sync` (no `finally: db.close()`).

Heartbeat: client-driven `ping`/`pong` (`routes/websockets.py:94-124`). Server has `emit_heartbeat` but doesn't schedule it.

## ML integration

Two parallel paths that disagree:
- **HTTP path** (`services/ml_service.py`): `httpx.AsyncClient` to `/ml/categorize`, `/ml/batch-categorize`, etc. — but ml-worker exposes no HTTP.
- **Celery path** (`routes/ml.py`): `celery_app.send_task('worker.classify_transaction')` then **blocking `result_async.get(timeout=30)`** inside async route.

Categorization triggered from `TransactionService.create_transaction` and `update_transaction` (training feedback).

## External services

- **Postgres** — sync psycopg2 over SQLAlchemy 2.0 typed mappings.
- **Supabase** — JWT verify, register/login/refresh/reset, webhooks.
- **Redis** — pub/sub, distributed locks (`SET NX EX`), cache helpers, Celery broker.
- **Plaid** — full SDK; access tokens encrypted at rest via `EncryptionService` (fail-soft → silent plaintext risk).

## Config & secrets

`Settings(BaseSettings)` (`config.py:15-228`):
- Loads `.env`, `../.env`, `../../.env` with `extra="ignore"` — typos silently ignored.
- Mixes `os.getenv(...)` with Pydantic env loading.
- `validate_required_settings` only checks `SECRET_KEY`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_WEBHOOK_SECRET`.
- Defaults: `ENABLE_ADMIN_BYPASS=true`, `RATE_LIMITING=false`, `CSRF_PROTECTION=false`.
- `PLAID_BASE_URL` referenced in code but **never defined in config**.

## Logging / observability

- Single `logging.basicConfig` at `main.py:33-40`.
- `request_id` generated (`main.py:155`) but never set on `request.state`; downstream uses fall back to header.
- `X-Process-Time` header attached.
- No structured logging, no correlation IDs across services, no metrics endpoint, no tracing.
- SQL echo logs full statements + params at DEBUG (`database.py:106-110`) — PII leak risk.

## Existing tests

`pyproject.toml` configures pytest with strict markers (`slow`/`integration`/`unit`).

Test files:
- `tests/conftest.py` (278 LOC) — **broken**: references non-existent `Account.institution_name`/`last_four`, lowercase enum strings, `/auth/login` (missing `/api`), non-existent `UserService.create_user`.
- `unit/test_budget_service.py`, `unit/test_transaction_service.py`, `unit/test_transaction_sync_service.py`, `unit/test_account_alert_service.py`.
- `integration/test_auth_router.py`, `integration/test_transaction_router.py`, `integration/test_transaction_service.py`, `integration/test_budget_service.py`, `integration/test_budget_edge_cases.py`, `integration/test_analytics_router.py`.

Uses **in-memory SQLite** — cannot exercise JSONB, ARRAY, Postgres enums, or `SET LOCAL`.

Untested entirely: dashboard, goals, notifications, ml, websockets, accounts_*, webhooks, users, categories, reconciliation, plaid trio, RLS, ML retry/backoff.
