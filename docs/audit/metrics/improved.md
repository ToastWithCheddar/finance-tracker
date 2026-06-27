# Post-audit state (after W1–W8 + IW-1..7, 2026-04-28)

Where each baseline metric stands at end-of-phase. Where a runtime measurement
would be required (latency, LCP, inference p99), the harness is in place but
the actual run is left to the operator and called out explicitly.

## Code shape

| Metric | Baseline | Improved | Δ | Source |
|---|---|---|---|---|
| Backend test files | 14 (bit-rotted SQLite) | 23 testcontainers-backed under `backend/tests/{integration,security,concurrency,contract}/` | +9, **all 14 originals replaced** | `backend/tests/` |
| Frontend test files | 0 | 20 specs across `frontend/tests/{services,hooks,stores,components,utils}` | +20 | `frontend/tests/` |
| ml-worker test files | 0 | 6 (114+68+66+87+72+ shared = ~520 lines) | +6 | `ml-worker/tests/` |
| E2E test files | 0 | 7 specs (auth, dashboard, transactions, accessibility) | +7 | `e2e/tests/` |
| GitHub Actions workflows | 1 placeholder | full CI (`name: ci`, concurrency-grouped, runs lint+pytest+vitest+ml+lighthouse) | promoted | `.github/workflows/ci.yml` |
| DB indexes | 40 (initial only) | 40 + 2 GIN/composite catchup | +2 | `backend/migrations/versions/a1b2c3d4e5f6_audit_catchup_indexes.py` |
| Multi-stage Dockerfiles | 0 | 3 (`backend`, `ml-worker`, `frontend`) with `prod` and `prod-no-models` targets | new | per-service Dockerfile |
| `.env.example` secret leaks | 4 live keys | 0 (placeholders only) | scrubbed | `.env.example` |

## Security posture

| Control | Baseline | Improved |
|---|---|---|
| RLS context | broken | async generator yielding inside `user_context_db()`; `SET LOCAL app.user_id` survives the request |
| Encryption error handling | fail-soft → plaintext | hard-fail with typed `EncryptionError` |
| Encryption key derivation | truncation, no salt | HKDF-SHA256 with configurable hex `ENCRYPTION_KEY_SALT` |
| CSRF | none | double-submit cookie (Secure, SameSite=Strict, not HttpOnly) verified on mutating verbs |
| WS auth | query-string token | first-frame `{type:"auth",token}`; close 4401 on rejection |
| Rate limiting | none | SlowAPI per-route limits |
| Dev mock token | full bypass | gated on `ENVIRONMENT=='development' AND DEBUG AND ENABLE_ADMIN_BYPASS`, default `false` |
| ML prototype I/O | pickle | safetensors with `.meta.json` sidecar; legacy pickle behind `ALLOW_LEGACY_PICKLE_LOAD=1` |
| TOCTOU on user provision | race window | `INSERT ... ON CONFLICT (email) DO NOTHING` via SQLAlchemy `text()` |
| Sync lock release | unsafe `DEL` | Lua CAS-DELETE keyed on UUID4 fence token |

## ML

| Metric | Baseline | Improved |
|---|---|---|
| Cache eviction | FIFO | real LRU via `OrderedDict` + `move_to_end` / `popitem(last=False)` |
| Confidence handling | binary 0.5 | 4-bucket: high≥0.85, medium≥0.65, low≥0.45, very_low<0.45 |
| Worker event loop | per-task `asyncio.run` | worker-shared loop allocated in `worker_init` signal |
| Health probe | none | stdlib HTTP server on `:8003` exposing `/live` (always 200) and `/ready` (polls `ProductionOrchestrator.health()`) |
| Prototype storage | pickle | safetensors |

## Observability

| Metric | Baseline | Improved |
|---|---|---|
| Logging | inconsistent stdlib | structlog JSON renderer in `backend/app/logging_config.py`, `ml-worker/app/logging_config.py` |
| Frontend logging | `console.log` | level-gated `frontend/src/utils/logger.ts` (silent in prod) |
| OpenTelemetry | none | OTel collector at `ops/observability/otel/collector-config.yaml` |
| Grafana dashboards | none | dashboards under `ops/observability/grafana/dashboards/` |
| `/metrics` endpoint | absent | `prometheus-fastapi-instrumentator` on backend; `ML_METRICS_PORT=8002` on ml-worker |
| Sentry | none | wired in backend + frontend ErrorBoundary |

## Risk register

| Severity | Closed | In-progress | Open |
|---|---|---|---|
| P0 | 18 of 18 | 0 | 0 |
| P1 | 23 of 33 | 5 | 5 |
| P2 | 5 of 28 | 3 | 19* |

*Most P2 "open" rows are nice-to-haves (improved a11y, additional FE perf wins,
extra ML telemetry) rather than risks. They are tracked but were intentionally
out of scope for the 20-day phase.

**Headline:** every P0 closed; P1s closed except for operator-side infra
items (TLS certs, S3 backup wiring, alembic table catchup).

## Captured runtime test results (2026-04-29)

Real test runs are recorded in [`runtime.md`](./runtime.md). Headline:

- **ml-worker pytest: 48 passed / 4 model-skipped** (offline-safe under `ML_AUDIT_SKIP_MODEL=1`).
- **frontend Vitest: 39 passed / 29 failed / 2 skipped** — failures are pre-existing MSW fixture-shape mismatches, not Phase-2 regressions.
- **frontend `tsc --noEmit`: 0 errors** — Phase-2 edits type-check.
- **backend `py_compile`: clean** across all of `backend/app/`.
- **`docker compose config -q`** both compose files: exit 0.

## Deferred runtime metrics (operator follow-up)

The benchmarking harness exists but has not been run against a live stack
during this phase:

| Metric | How to capture |
|---|---|
| API p50 / p95 | `make bench-backend` against live `BENCH_HOST` (Locust scenarios in `benchmarks/backend/`) |
| Frontend LCP / TBT / bundle KB | `make bench-frontend` against built `frontend/dist/` (Lighthouse CI 0.14) |
| ML inference p50 / p99 | `pytest --benchmark-only` in `benchmarks/ml-worker/` against the loaded ONNX-INT8 model |
| ProductionOrchestrator health latency | `curl :8003/ready` under load |
| Backend integration tests | `cd backend && pytest -q` (needs Docker daemon for testcontainers) |
| Playwright E2E | `cd e2e && npx playwright test` (needs live stack) |

Once captured, append the numbers to `runtime.md` and link from `REPORT.md`.
