# Section A — Performance

**Owner agent:** Opus 4.7, medium effort. Two parallel sub-agents (backend + frontend). High effort only if profiling produces ambiguous results.

## Scope

Findings: BE-PERF-001..008, BE-SEC-008 (event-loop blocking), FE-PERF-001..006, ML-PERF-001 (handed off to Section F for execution).

## Backend tasks

1. **Unblock event loop** (BE-PERF-001, BE-SEC-008)
   - Change `routes/ml.py:60` to `await loop.run_in_executor(None, result_async.get, 30)` as a stopgap, then refactor to fire-and-forget with WS delivery.
   - Wrap `supabase.client.auth.get_user()` calls in executor or migrate to Supabase async client (`auth/auth_service.py:153`, `auth/dependencies.py:105`).

2. **Add indexes** (BE-PERF-003, 004, 008) via a new Alembic revision
   - GIN on `transactions.tags`.
   - Composite `(user_id, status, transaction_date)` on `transactions`.
   - Functional index on `func.abs(transactions.amount_cents)` if filter usage is confirmed via `pg_stat_statements`.

3. **Dashboard caching** (BE-PERF-005)
   - Cache `/dashboard/summary` per user with 30-second TTL via Redis.
   - Replace serial `count()` calls with a single aggregate query using `case when` clauses.

4. **Async DB driver evaluation** (BE-PERF-002)
   - Spike: convert one route group (e.g. `/api/categories`) to asyncpg + SQLAlchemy 2 async.
   - Benchmark before/after via `benchmarks/backend/locust_dashboard.py`.
   - Decision document under `docs/runbooks/async-db-decision.md`.

5. **Redis hygiene** (BE-PERF-006, 007)
   - Reuse a long-lived `redis.Redis` connection in `core/redis_client.py` instead of `pool.get_connection()`/`close()` per call.
   - Replace WS subscriber `pubsub.get_message(timeout=1.0) + sleep(0.01)` with `pubsub.listen()` async iterator.

## Frontend tasks

1. **Production build hygiene** (FE-PERF-001, FE-PR-001)
   - `vite.config.ts`: `build.minify = 'esbuild'`, `build.sourcemap = 'hidden'` (uploaded to Sentry only), `define.__DEV__ = JSON.stringify(mode === 'development')`.

2. **Code splitting** (FE-PERF-002)
   - Wrap each route in `React.lazy(() => import(...))` + Suspense fallback to existing `LoadingSpinner`.
   - Verify with bundle visualizer that Recharts and Nivo end up in separate chunks.

3. **Virtualize long lists** (FE-PERF-003)
   - Adopt `react-window` for `TransactionList` with `FixedSizeList`. Item height comes from existing `TransactionItem` measured in tests.

4. **Eliminate duplicate hydration** (FE-PERF-004)
   - Single source of truth: WS `onopen` triggers backfill; remove the dashboard `useEffect` that re-fetches the same data.

5. **Cache layer cleanup** (FE-PERF-005)
   - Strip in-memory cache from `BaseService`. Rely on React Query.

6. **Bound the unbounded** (FE-PERF-006)
   - Cap `realtimeStore.transactionUpdates` at 50 with sliding-window logic mirroring `recentTransactions`.

## Deliverables

- New Alembic revision under `backend/migrations/versions/` (the migration itself touches internship code; allowed per change-scope decision).
- `benchmarks/backend/` Locust + pytest-benchmark harnesses, baseline report.
- `benchmarks/frontend/` bundle visualizer snapshot, Lighthouse CI config.
- `docs/runbooks/async-db-decision.md` with measurements.

## Success metrics

- p95 `/api/dashboard/summary` < 200 ms with 50 RPS.
- Frontend initial JS payload < 350 KB gzipped (currently unmeasured but ~2-5 MB unminified).
- Lighthouse perf > 85 on Dashboard.
- ML route p99 < 500 ms (delegated to Section F).

## Agent prompt template

> You are working on the finance-tracker production-hardening audit. Use Claude Opus 4.7 with medium-effort thinking. Read `docs/audit/snapshot/`, `docs/audit/findings.csv`, and `docs/audit/improvement-sections/A-performance.md` first. Then execute the [backend|frontend] tasks listed there. New artifacts go under `benchmarks/` and `docs/runbooks/`. You may modify internship code where required by the task list (e.g. `vite.config.ts`, `routes/ml.py`, model index migrations). Track every fix in `docs/audit/findings.csv` (status → closed, add commit SHA). Report deliverables vs success metrics at the end.
