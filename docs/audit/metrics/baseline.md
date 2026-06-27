# Pre-audit baseline (W1 snapshot, 2026-04-08)

These numbers are what the codebase looked like at the **start** of the
production-hardening phase. They are derived from `docs/audit/snapshot/`
(the W1 frozen snapshot) and from git history, not from a live stack.

> Note: latency/throughput numbers (API p50/p95, FE LCP/TBT, ML p99) are
> *deferred* — they require a live, populated stack and a load generator
> we did not stand up locally during the phase. Operator follow-up: run
> `make bench-backend` against the live stack and `make bench-frontend`
> against a built frontend.

## Code shape

| Metric | Baseline value | Source |
|---|---|---|
| Backend test files (real) | 14 (all SQLite-mocked, bit-rotted) | `backend/tests/` pre-replacement |
| Frontend test files (Vitest) | 0 | repo had `jest.config.js` only, no specs |
| ml-worker test files | 0 | no `tests/` dir existed |
| E2E test files | 0 | Playwright wasn't installed |
| GitHub Actions workflows | 1 (0-byte `ci.yml` placeholder) | repo root |
| DB indexes | 40 (initial schema only, in `0ebba5935295_initial_schema.py`) | alembic |
| Multi-stage Dockerfiles | 0 (single-stage dev images only) | `backend/Dockerfile`, `ml-worker/Dockerfile`, `frontend/Dockerfile` pre-W6 |
| `.env.example` secret leaks | live `SECRET_KEY`, `SUPABASE_ANON_KEY`, `PLAID_CLIENT_ID`, `PLAID_SECRET` | git blame |

## Security posture

| Control | Baseline state |
|---|---|
| RLS context | broken — `user_context_db` exited *before* yielding (BE-SEC-001) |
| Encryption error handling | fail-soft → returned plaintext (BE-SEC-003) |
| Encryption key derivation | `secrets.token_urlsafe(SECRET_KEY)` truncation, no salt |
| CSRF | none — no token mechanism on mutating verbs |
| WS auth | token in query string; no handshake validation (BE-WS-001) |
| Rate limiting | none on routes |
| Dev mock token | full bypass on `ENVIRONMENT=='development'` (BE-SEC-002) |
| ML prototype I/O | `pickle.load` on disk file (ML-SEC-001) |
| TOCTOU on user provision | `SELECT then INSERT` race window (BE-CONC-001) |
| Sync lock release | `DEL` regardless of holder (BE-CONC-002) |

## ML

| Metric | Baseline state |
|---|---|
| Cache eviction | FIFO masquerading as LRU (ML-PERF-001) |
| Confidence handling | binary 0.5 threshold, no buckets (ML-PERF-001) |
| Worker event loop | `asyncio.run` per task (process churn) |
| Health probe | none (no `/live` or `/ready`) |
| Prototype storage | pickle (ML-SEC-001) |

## Observability

| Metric | Baseline state |
|---|---|
| Logging | stdlib `logging` per module, format inconsistent (BE-LOG-001..003) |
| Frontend logging | `console.log` calls reach prod bundles (FE-LOG-001) |
| OpenTelemetry | not wired |
| Grafana dashboards | none |
| `/metrics` endpoint | absent (INFRA-OBS-002) |
| Sentry | not wired |

## Risk register

- **79 findings** logged in `docs/audit/findings.csv` at end of W2.
- **0 closed** (status snapshot at start of W3).
- Severity breakdown: 18×P0, 33×P1, 28×P2.
