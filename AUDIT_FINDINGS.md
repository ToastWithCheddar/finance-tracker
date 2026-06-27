# Audit Findings & Remediation

_A code-review pass over the whole repository, with the genuine issues fixed and the
rest framed as a roadmap. Written to be spoken from in a final assessment: it leads
with what's solid, is honest about what's open, and separates "internship-acceptable"
from "real concern."_

Severity scale: **Critical** (would cause data loss / security breach) · **High**
(real bug or risk) · **Medium** (should fix) · **Low** (polish). Each item notes
whether it is **internship-acceptable** (fine for this context) or a **genuine
concern** (would matter in production).

---

## TL;DR for the presentation

- The codebase is in **good shape for an internship project** — it already has RLS,
  encryption at rest, CSRF, rate limiting, observability, and a real test pyramid.
- This pass **fixed 7 real backend/frontend issues** and **cleaned up the test tooling
  and documentation**, including adding the missing top-level README.
- Two of the scariest-sounding findings from the automated scan turned out to be
  **false alarms** — verified and dismissed (see below). Being able to say *why* they're
  false is itself a good talking point.
- A short, honest **roadmap** of deliberately-deferred items remains (httpOnly auth
  cookies, real TLS, off-site backups). These are documented, not forgotten.

---

## Corrected false alarms (verified, not real)

| Claim | Reality |
|---|---|
| "`.env` with real secrets is committed to git" | **False.** `.env` is in `.gitignore` and `git ls-files`/`git log --all -- .env` confirm it was **never** tracked. The local file is normal; nothing leaked. |
| "Broken import: `seed_data.py` was deleted but is still imported" | **False.** `backend/app/main.py` imports `app.scripts.seed_data`, which exists. The deleted `app/seed_data.py` was a stale duplicate. |

Knowing the difference between "a scanner flagged it" and "it is actually true" is the
point — both were checked against the repo directly.

---

## Fixed in this pass

### Backend

| # | Severity | Issue | Fix | Where |
|---|---|---|---|---|
| BE-SEC-008 (extended) | High · genuine | Several `async def` auth methods called the **synchronous** Supabase SDK, blocking the FastAPI event loop on every login/register/password change. | Routed all Supabase calls through `run_in_executor`, extending the pattern already used by `refresh_token`. | `backend/app/auth/auth_service.py` |
| BE-WS-001 | Medium · genuine | The WebSocket manager mutated/iterated its connection map without a guard. | Added an `asyncio.Lock` around structural changes; fan-out takes a snapshot under the lock and sends **outside** it (no head-of-line blocking). | `backend/app/websocket/manager.py` |
| BE-SEC-009 | Medium · genuine | Supabase webhook secret compared with `!=` (timing-attackable). | Switched to `secrets.compare_digest`. | `backend/app/auth/dependencies.py` |
| BE-SEC-003b | Medium · genuine | Encryption salt silently regenerated when unset — in production this would orphan every previously-encrypted secret (e.g. Plaid tokens) on restart. | Now **fails fast** in production if `ENCRYPTION_KEY_SALT` is unset; dev keeps the loud-warning fallback. | `backend/app/services/encryption_service.py` |
| BE-QUAL-001 | Low–Medium · genuine | 10 bare `except:` clauses swallowing errors (incl. catching `KeyboardInterrupt`). | Replaced with specific exception types; the DB error-status writer now logs and rolls back instead of silently passing. | `account_sync_monitor.py`, `reconciliation_service.py`, `plaid_client_service.py`, `transaction_sync_service.py`, `routes/websockets.py` |

### Frontend

| # | Severity | Issue | Fix | Where |
|---|---|---|---|---|
| FE-SEC-010 | Medium · genuine | `logout()` cleared auth state but not the React Query cache synchronously — a brief window where the next user could see the previous user's cached data. | `logout()` now calls `queryClient.clear()` immediately. | `frontend/src/stores/authStore.ts` |
| FE-LOG-001 | Low · genuine | `console.debug?.()` calls bypassed the production-safe logger and would print in prod builds; dashboard debug logs used `logger.info` (noisy in prod). | Routed through `logger.debug` (no-op/Sentry-breadcrumb in prod). | `transactionService.ts`, `realtimeStore.ts`, `RealtimeDashboard.tsx` |
| FE-PR-004 (partial) | Low · acceptable | ~148 `any` casts. | Typed the load-bearing register-response parse in `authStore.ts`; the rest remain (see roadmap). | `frontend/src/stores/authStore.ts` |

### Tooling & docs

- **Test runner consolidated.** There were two parallel suites: a maintained **Vitest**
  suite under `frontend/tests/` (what CI runs, 20 files) and an **orphaned jest** suite
  under `src/**/__tests__/` (5 files, never run by CI, using a different framework).
  Removed the orphaned jest suite + `jest.config.js`, repointed the `npm test` scripts
  to Vitest so local `npm test` matches CI, and fixed the Makefile/RUN.md references.
- **Backend test layout** — confirmed the staged deletions under `backend/tests/` are
  the **old** unit layout being replaced by the richer untracked suite (security,
  concurrency, contract). Intentional, healthy.
- **Documentation** — added the missing top-level [`README.md`](README.md); fixed stale
  facts in `frontend/README.md` (React 18 → 19, dev port 5173 → 3000, "Day 4" notes →
  current feature list); marked `internship.md`/`newreport.md` as historical so they
  aren't mistaken for current state.

---

## Roadmap — deliberately deferred (good "what I'd do next" slide)

| Severity | Item | Why deferred |
|---|---|---|
| High · genuine | **Move auth tokens from `sessionStorage` to httpOnly, Secure, SameSite cookies.** | Cross-cutting backend + frontend change; the right call but larger than a hardening pass. The bounded event-loop/cache fixes above were done now. |
| Medium · acceptable | **Finish the ~148 `any` sweep** and enable `noUnusedLocals`/`noUnusedParameters` in `tsconfig.app.json`. | Flipping strictness across 147 files is a large, separate cleanup; risks destabilizing the build. |
| Medium · acceptable | **Make DB pool size, sync-lock timeout, and Plaid JWKS caching env-configurable.** | Hardcoded values work for this scale; parameterize before real load. |
| Medium · genuine | **ML worker `pickle` → `safetensors` migration.** | Migration already in progress in the code (compat path exists). |
| Low · acceptable | **Prune now-unused jest devDependencies** (`jest`, `ts-jest`, etc.) from `frontend/package.json`. | Left in place to avoid a 10k-line lockfile churn during this pass; a one-line `npm uninstall` follow-up. |
| — operator | **Real TLS certs, off-site (S3) backups, multi-worker caching.** | Tracked as operator-deferred in `docs/runbooks/security-checklist.md` and `docs/audit/findings.csv`. |

---

## Strengths worth highlighting

- **Security:** Postgres row-level security with per-request user context, Fernet
  encryption at rest (HKDF-SHA256), CSRF double-submit, rate limiting, and a gated
  dev-bypass that cannot activate in production.
- **Reliability:** Redis distributed lock with fence tokens (CAS-delete), graceful
  WebSocket lifecycle, structured logging, Prometheus/Grafana/Loki observability stack.
- **Testing:** a genuine pyramid — pytest with **testcontainers** (real Postgres/Redis),
  dedicated security/concurrency/contract suites, Vitest + MSW on the frontend, and
  Playwright e2e.
- **Documentation:** a tracked risk register (`docs/audit/findings.csv`, ~74 closed),
  per-wave changelogs, operational runbooks, and architecture diagrams.

For the full historical register see [`docs/audit/findings.csv`](docs/audit/findings.csv);
this document captures the most recent review and the changes made in it.
