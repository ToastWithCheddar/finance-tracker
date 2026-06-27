# `audit/` — Post-Internship Production Hardening

This folder is the **single home for all post-internship work** on `finance-tracker`. Everything inside this directory was created after the internship ended; nothing inside this directory existed at the time of the internship deliverable.

## Modularity rule (non-negotiable)

The original internship code lives at the repo root (`backend/`, `frontend/`, `ml-worker/`, `nginx/`, `scripts/`, `docker-compose*.yml`, `ci.yml`). That code is the deliverable that was submitted.

**All new artifacts** — tests, benchmarks, audit reports, logging configs, CI workflows, runbooks, refactoring proposals, and so on — go **here**, under `audit/`. The intent is:

1. The internship deliverable stays browsable and untouched in its original form.
2. The post-internship work is auditable as a single unit.
3. The post-internship work is removable as a single unit (`rm -rf audit/`) without breaking the internship deliverable.

When fixes to internship code are unavoidable (e.g. patching a security bug in `backend/app/auth/dependencies.py`), the fix is tracked here in `10-findings/findings.csv` with the commit SHA, but the change itself lands in the original file. **All net-new files always live under `audit/`.**

## Layout

```
audit/
├── README.md                              ← you are here
├── 00-snapshot/                           ← frozen description of repo as of audit start
├── 10-findings/                           ← canonical risk register
├── 20-improvement-sections/               ← per-pillar agent briefs (A–F)
├── 30-tests/                              ← net-new test suites (pytest, vitest, playwright)
├── 40-benchmarks/                         ← perf harnesses + reports
├── 50-logging/                            ← proposed observability config
├── 60-ci/                                 ← net-new GH Actions workflows
└── 70-runbooks/                           ← ops/runbook docs
```

## Four pillars

The post-internship work is organized into four pillars, mapped to improvement sections A–F:

| Pillar | Sections |
|---|---|
| Performance | A, F |
| Extensive testing | B |
| Clean logging / observability | C |
| Production readiness | D, E (security) |

## Tooling decisions

- **Backend tests:** pytest + `testcontainers[postgres,redis]` (real Postgres, no SQLite illusions).
- **Frontend tests:** Vitest + RTL + MSW (existing `jest.config.js` left untouched in `frontend/`).
- **E2E:** Playwright against a docker-compose test stack.
- **ML-worker tests:** pytest + parity tests (PyTorch vs ONNX-INT8).
- **Benchmarks:** Locust (backend), Lighthouse CI (frontend), custom harness (ml-worker).
- **Logging:** structlog (backend, ml-worker), Sentry/GlitchTip (frontend), Prometheus + OpenTelemetry.

## Agent orchestration

All future work is executed by Claude Opus 4.7 subagents at **medium effort** by default; **high effort** is reserved for debugging-heavy sections (E security, F ML revival). The orchestrator coordinates parallel agents per wave; see `20-improvement-sections/` for individual briefs.
