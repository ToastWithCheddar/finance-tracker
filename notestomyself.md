Schedule-based implementation audit (Days 1–12)

Note: For each day, one focal task is assessed for correctness, structure, cross-file connections, and fixes.

Day 1 – Project Setup & Infrastructure (Focus: Docker & secrets)
- What exists: `docker-compose.yml` wiring for Postgres, Redis, backend, frontend, ml-worker, nginx. Backend Dockerfile non-root user. Frontend Dockerfile multi-stage.
- Correctness: Partially. Secrets are hardcoded/defaulted; Nginx path bug; Redis not internal-only; debug flags enabled; healthchecks moderate.
- Structure and connections: Services networked on `finance-network`. Backend mounts code with reload; WS needs upgrade headers; ML worker not exposed as HTTP (Celery only).
- Fixes: Move secrets to env/secrets; add profiles; restrict ports in prod; correct Nginx `/api/auth` proxy; add WS location; pin resource limits; enable restart policies per env.

Day 2 – DB & Backend Foundation (Focus: schema & migrations integrity)
- What exists: SQLAlchemy models under `backend/app/models`, Alembic migrations present, `Base` in `database.py`. Health checks implemented.
- Correctness: Mostly fine, but raw DDL for indexes/triggers in `database_manager.py` bypasses migrations; SQLite PRAGMA hook noise.
- Structure and connections: `Base.metadata.create_all` run at startup (dev). Seed categories script invoked.
- Fixes: Move DDL to Alembic; gate `create_all` by env; keep all DDL in migrations; add DB URL validation and fail-fast in prod.

Day 3 – Authentication System (Focus: Auth paradigm alignment)
- What exists: Supabase-only auth flow (no custom JWT); dependencies verify tokens via Supabase; FE store still expects tokens on register; email verify handled by Supabase.
- Correctness: Mismatch with plan (“JWT middleware”). Implementation is fine for Supabase but FE and docs assume JWT.
- Structure and connections: `auth_service.py`, `dependencies.py`, `supabase_client.py`, `frontend/src/stores/authStore.ts`.
- Fixes: Make FE register not set tokens; ensure refresh uses Supabase; update docs to reflect Supabase-only; optionally add MFA per Supabase.

Day 4 – Frontend Foundation (Focus: Security posture and env)
- What exists: React+Vite TS, Tailwind, Zustand, TanStack Query; components and pages scaffolded.
- Correctness: Token logging present; CSP missing; env validator OK; CSRF header unused server-side.
- Structure and connections: `apiClient` integrates cookies/sessionStorage; global query client.
- Fixes: Remove token logs; add CSP via Nginx; either implement CSRF or remove; tighten CORS in prod.

Day 5 – Transaction Management Backend (Focus: Filtering/sorting contract)
- What exists: CRUD endpoints, CSV import, search and filters, pagination; WS sends on changes.
- Correctness: Category name hardcoded; limited sort options; no idempotency for imports; WS manager duplication breaks notifications.
- Structure and connections: `transaction_service.py`, `routes/transaction.py`, `websocket/manager.py`.
- Fixes: Join category; add sort params; add idempotency keys; use global `websocket_manager` only.

Day 6 – Account Management (Focus: Plaid sandbox linking E2E)
- What exists: Enhanced Plaid service with correct `item/public_token/exchange`, link token creation, balance/transactions sync scaffolding, sync monitor and scheduler; FE Plaid components exist.
- Correctness: No backend webhook endpoint; Nginx proxy path bug; WS event payloads mismatched; environment creds blank; sandbox testing likely not wired.
- Structure and connections: `enhanced_plaid_service.py`, `routes/accounts.py`, `usePlaid.ts`, `PlaidLink.tsx`, `AccountConnectionStatus.tsx`.
- Fixes: Implement `/api/webhooks/plaid`; fix Nginx; align WS payloads; configure sandbox creds via env; add test mode and mocked responses for dev without external calls.

Day 7 – Real-time WebSocket System (Focus: Server path/middleware correctness)
- What exists: Rich schemas and events; manager with Redis persistence; FE hook with backoff and dedupe.
- Correctness: Router not mounted; endpoint path mismatch (`/ws` vs `/ws/realtime`); token in query; duplicate manager instances; payload shape mismatch.
- Structure and connections: `routes/websockets.py`, `websocket/manager.py`, `websocket/events.py`, FE `useWebSocket.ts`.
- Fixes: Mount WS router at `/ws/realtime`; switch to header-based auth; standardize `{type, payload}`; use single `websocket_manager`; add Nginx WS block.

Day 8 – ML Classification System (Focus: Service availability mismatch)
- What exists: ML worker is a Celery app with tasks; backend ML client expects HTTP endpoints at `ML_SERVICE_URL` (`/ml/categorize`, etc.).
- Correctness: Mismatch. There is no HTTP server in `ml-worker` responding to those routes; calls will fail.
- Structure and connections: `ml-worker/worker.py` (Celery), `backend/app/services/ml_client.py` (httpx to HTTP service), `routes/ml.py`.
- Fixes: Add a FastAPI service in `ml-worker` (or within backend) exposing `/ml/*` that forwards to Celery or runs in-process model; or change backend client to publish Celery tasks and await results (with timeouts). Update compose to expose ML HTTP service at 8001.

Day 9 – Dashboard & Analytics (Focus: Data shape and correctness)
- What exists: Backend analytics builder; FE charts and dashboard; filters wired.
- Correctness: Dollars vs cents inconsistencies; placeholder categories; potential date timezone drift; WS issues hinder “live”.
- Structure and connections: `TransactionService.get_dashboard_analytics`, FE `useDashboard` hooks and charts.
- Fixes: Normalize to cents in API, convert at FE; join categories; timezone-aware dates; verify keys consumed by FE; add contract tests.

Day 10 – Budget System with Real-time Alerts (Focus: Alerts delivery)
- What exists: Budget CRUD, progress, summary, alerts endpoints; FE components; WS events prepared.
- Correctness: Alerts rely on WS, currently unreliable; threshold/period logic OK but needs tests; over-budget filtering implemented.
- Structure and connections: `routes/budget.py`, `budget_service.py`, `websocket/events.py`.
- Fixes: Stabilize WS; add email fallback for critical alerts; add unit tests for alert thresholds and periods.

Day 11 – Goals & Savings (Focus: Progress integrity)
- What exists: Goals API/components (files present); milestone notifications.
- Correctness: Needs verification that progress calculations use same currency units and timezone; ensure achievement checks idempotent and not re-firing.
- Structure and connections: `backend/app/routes/goals.py`, `frontend/components/goals/*`.
- Fixes: Add tests for progress calc; store milestone/achievement audit to avoid duplicate celebrations; send summary in WS payloads.

Day 12 – Enhanced Account Features (Focus: Automatic sync completeness)
- What exists: Transaction sync and monitor services; scheduler; FE status components.
- Correctness: Jobs not persisted; no Plaid webhooks; immediate sync endpoint present; status indicators depend on metadata which may be stale.
- Structure and connections: `automatic_sync_scheduler.py`, `account_sync_monitor.py`, `routes/accounts.py`, FE `AccountConnectionStatus.tsx`.
- Fixes: Persist scheduler jobs; implement Plaid webhooks; add idempotent sync and error backoff; surface per-account sync history in FE; add manual relink flow (update link token).


