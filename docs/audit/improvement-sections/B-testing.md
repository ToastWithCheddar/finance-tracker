# Section B — Extensive Testing

**Owner agents:** Opus 4.7, medium effort. Three parallel sub-agents (backend tests, frontend tests, e2e). High effort if testcontainers integration produces flakes.

## Scope

Findings: BE-TEST-001..005, FE-TEST-001, ML-TEST-001 (latter handed to F for parity tests).

## Tooling

| Layer | Stack |
|---|---|
| Backend | pytest, pytest-asyncio, pytest-cov, hypothesis, testcontainers[postgres,redis], respx (httpx mock), faker, factory-boy |
| Frontend | vitest, @testing-library/react, @testing-library/user-event, @testing-library/jest-dom, msw (HTTP mock), happy-dom |
| E2E | Playwright @latest, docker-compose stack via `docker-compose.test.yml` |
| ML-worker | pytest, pytest-celery (eager + Redis), numpy assertions |

The existing `frontend/jest.config.js` and `backend/tests/` are **not modified**. New tests live under `tests (per-package)/`.

## Backend layout (`backend/tests/`)

```
backend/
├── conftest.py                  # session-scoped Postgres + Redis containers, app override
├── pyproject.toml               # separate pytest config, dependency pins
├── factories/                   # factory-boy factories for all models
├── unit/
│   ├── test_encryption_roundtrip.py        # Hypothesis property tests (BE-SEC-003)
│   ├── test_validators.py
│   ├── test_secure_storage_helpers.py
│   └── test_schema_normalization.py
├── integration/
│   ├── test_health.py
│   ├── test_auth_flow.py                   # full register-login-refresh-change-password
│   ├── test_transactions_router.py         # all endpoints incl. /export bounds
│   ├── test_dashboard_router.py
│   ├── test_categories_router.py
│   ├── test_users_router.py
│   ├── test_budgets_router.py
│   ├── test_goals_router.py
│   ├── test_notifications_router.py
│   ├── test_accounts_basic_router.py
│   ├── test_accounts_sync_router.py
│   ├── test_accounts_reconciliation_router.py
│   ├── test_ml_router.py                   # patches Celery to eager
│   ├── test_websockets_router.py           # uses websockets client + Redis
│   └── test_webhooks_router.py             # supabase + plaid (with respx)
├── contract/
│   ├── fixtures/plaid/                     # captured sandbox responses
│   ├── fixtures/supabase/
│   ├── test_plaid_link_exchange.py
│   ├── test_plaid_sync.py
│   └── test_supabase_jwt_verify.py
├── security/
│   ├── test_rls_user_context.py            # BE-SEC-001 — asserts setting persists across queries
│   ├── test_rls_cross_user_leak.py         # BE-SEC-001 — negative test
│   ├── test_dev_bypass_disabled_in_prod.py # BE-SEC-002
│   ├── test_rate_limits.py                 # BE-RL-001
│   ├── test_admin_ws_endpoints_guarded.py  # BE-SEC-007
│   └── test_export_dos_bounds.py           # BE-SEC-009
└── concurrency/
    ├── test_user_provisioning_race.py      # BE-CONC-001 (asyncio.gather of N parallel logins)
    ├── test_seed_idempotent_under_load.py  # BE-PR-006
    └── test_sync_lock_fence_token.py       # BE-CONC-002
```

`conftest.py` will:
- Start `PostgresContainer("postgres:15-alpine")` once per session, run `Base.metadata.create_all`, yield session-scoped engine.
- Start `RedisContainer("redis:7-alpine")` similarly.
- Override `app.dependency_overrides[get_db]` and Redis client factory.
- Mock Supabase via respx (`httpx_mock` for `https://<project>.supabase.co/auth/v1/*`).
- Provide `authenticated_client` fixture that posts to a real `/api/auth/login` against a respx-mocked Supabase.

## Frontend layout (`frontend/tests/`)

```
frontend/
├── vitest.config.ts             # happy-dom env, path aliases match Vite config
├── setup.ts                     # MSW server, RTL setup, jest-dom matchers
├── msw/
│   ├── handlers.ts              # baseline /api/* handlers
│   └── server.ts
├── services/
│   ├── api.test.ts              # refresh interceptor, snake/camel mismatch (FE-SEC-003)
│   ├── transactionService.test.ts  # snake↔camel normalization, cents handling
│   ├── budgetService.test.ts
│   ├── plaidService.test.ts
│   └── secureStorage.test.ts
├── hooks/
│   ├── useTransactions.test.ts  # invalidation patterns (FE-PR-005)
│   ├── useBudgets.test.ts
│   ├── useWebSocket.test.ts     # heartbeat, reconnect, message dispatch
│   └── usePlaid.test.ts
├── stores/
│   ├── authStore.test.ts        # login, refresh, logout, persist
│   ├── realtimeStore.test.ts    # handleWebSocketMessage matrix, dedupe TTL
│   └── themeStore.test.ts
└── components/
    ├── ui/CurrencyInput.test.tsx     # cents normalization end-to-end
    ├── ui/Modal.test.tsx             # focus trap, escape, a11y
    ├── transactions/TransactionForm.test.tsx
    ├── dashboard/RealtimeDashboard.test.tsx
    └── common/ErrorBoundary.test.tsx
```

## E2E layout (`e2e/`)

```
e2e/
├── playwright.config.ts         # webServer: docker compose up -f compose.test.yml
├── fixtures/
│   ├── plaid-sandbox.ts
│   └── seeded-user.ts
└── specs/
    ├── auth.spec.ts             # register + verify (mock) + login + logout
    ├── plaid-link.spec.ts       # connect sandbox bank, see accounts
    ├── transactions.spec.ts     # list, filter, edit, bulk delete
    ├── budgets.spec.ts
    ├── dashboard-realtime.spec.ts  # WS push from another tab updates this tab
    └── csv-import.spec.ts
```

## ML-worker tests (handed to Section F for execution)

Cross-reference `F-ml-worker-revival.md`.

## Deliverables

- All directories above populated with tests.
- `Makefile` with targets `audit-test-backend`, `audit-test-frontend`, `audit-test-e2e`, `audit-test-all`.
- Coverage report HTML in `tests (per-package)/.coverage/` (gitignored).
- Coverage gate: backend ≥ 75% on `app/services/*` and `app/routes/*`; frontend ≥ 70% on `services/*` and `stores/*`.

## Success metrics

- All tests green on a fresh clone via `make audit-test-all`.
- Existing `backend/tests/` and `frontend/jest` runs are not affected.
- Every P0 finding has at least one test that proves the fix (added to the same PR as the fix).

## Agent prompt template

> Working on finance-tracker production-hardening audit. Opus 4.7 medium effort. Read `docs/audit/snapshot/`, `docs/audit/findings.csv`, `docs/audit/improvement-sections/B-testing.md`. Execute the [backend|frontend|e2e] sub-tree listed there. All new tests under `tests (per-package)/`; do not modify `backend/tests/` or `frontend/src/__tests__/`. Pin tooling in `tests (per-package)/<layer>/{pyproject.toml|package.json}`. After authoring, run `make audit-test-<layer>` and report failures. Update findings.csv with `status=test-added` for items now covered.
