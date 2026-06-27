# Audit-to-main integration — wave index

The `audit/` directory was a temporary staging ground used during the
production-hardening phase to keep new work clearly separated from the
original internship deliverable. Once everything was reviewed, it was
integrated into canonical homes across the repo and the staging directory
was deleted.

The historical "keep new audit work in a separate modular folder" rule
(memory note `feedback_modular_audit_folder.md`) was retired on 2026-04-27
because, with everything integrated, future edits should land directly in
canonical locations rather than in a parallel folder.

## Waves

- **[01-tests-integration.md](01-tests-integration.md)** — IW-1: moved the test
  suites from `audit/30-tests/{backend,frontend,ml-worker,e2e}` into
  `backend/tests/`, `frontend/tests/`, `ml-worker/tests/`, and the new
  top-level `e2e/`. Clean Postgres + Redis testcontainers pipeline.
- **[02-ci-promotion.md](02-ci-promotion.md)** — IW-2: promoted
  `audit/60-ci/workflows/audit.yml` to `.github/workflows/ci.yml`,
  `audit/60-ci/Makefile` to repo-root `Makefile`, and the docker-compose
  stacks (`prod`, `observability`) to repo root.
- **[03-observability.md](03-observability.md)** — IW-3: integrated otel
  collector / grafana / loki configs into `ops/observability/`, made
  `backend/app/logging_config.py`, `ml-worker/app/logging_config.py`, and
  `frontend/src/utils/logger.ts` canonical (no longer "duplicates of" anything).
- **[04-runbooks-and-docs.md](04-runbooks-and-docs.md)** — IW-4: moved
  `audit/70-runbooks/` to `docs/runbooks/` and `audit/00-snapshot/`,
  `audit/10-findings/`, `audit/20-improvement-sections/` to `docs/audit/`.
- **[05-benchmarks.md](05-benchmarks.md)** — IW-5: moved
  `audit/40-benchmarks/{backend,frontend,ml-worker}/` to top-level
  `benchmarks/`.
- **[06-cleanup.md](06-cleanup.md)** — IW-6: swept the remaining 26 stale
  `audit/(00-..70-)` references across the repo, rewrote each to its
  canonical destination, deleted the now-orphan `audit/` tree (~41k files,
  almost entirely a leftover `.venv` and `node_modules`), retired the
  modular-folder MEMORY rule.
- **[07-verification.md](07-verification.md)** — IW-7: final static
  verification (compose configs parse, CI YAML valid, Makefile targets
  rewritten, no stale `audit/` references outside the intentional CI
  provenance comment). Live test/bench/e2e runs deferred to operator
  (require Docker / built frontend / live stack).

## Why the modular rule was retired

The original rationale ("repo was an internship deliverable; keep what was
submitted clearly separated from what was added afterward") served its
purpose during the audit/staging phase. With everything reviewed and
integrated, maintaining a parallel `audit/` tree would have meant either
duplicating files or perpetually confusing readers about which copy was
canonical. The new policy: edit in canonical locations directly. The
"what was added afterward" distinction now lives in git history and in
these wave changelogs rather than in a parallel directory.

## 25-day phase complete (2026-04-29)

The production-hardening phase, originally scoped at 20 days and extended
by three days of Phase-2 closeout, wrapped on 2026-04-29. The end-of-phase
narrative report — analogous to `internship.md` from the prior 40-day
phase but written in Turkish and tied to the bulgu IDs in
`docs/audit/findings.csv` — lives at the repo root as `REPORT.md` and
covers 12 sections.

### Phase-2 closeout waves (added 2026-04-29)

- **[08-backend-hygiene.md](08-backend-hygiene.md)** — IW-08 / Day 21:
  closed BE-PR-003, BE-PR-004, BE-WS-001, BE-WS-002, INFRA-CI-002,
  BE-PERF-008. Documented BE-PERF-002 follow-up plan.
- **[09-frontend-hygiene.md](09-frontend-hygiene.md)** — IW-09 / Day 22:
  closed FE-PR-002, FE-PR-003, FE-PR-005, FE-WS-001 (per-route
  ErrorBoundary, autoConnect short-circuit, unified queryKeys).
- **[10-a11y.md](10-a11y.md)** — IW-10 / Day 23: closed FE-A11Y-001
  (axe-playwright sweep extended from 2 to 7 routes), bumped REPORT,
  INDEX, MEMORY.

### Closeout artifacts produced beyond the ten integration waves

- `REPORT.md` (Turkish narrative, 12 sections, day-by-day mapping)
- `docs/audit/metrics/{baseline,improved}.md` (before/after numbers)
- `docs/audit/diagrams/{security-topology,observability-flow,test-pyramid,prod-compose}.md` (Mermaid)
- `docs/audit/improvement-sections/G-accessibility.md` (added Day 23)
- `docs/audit/findings.csv` (final state: 70 closed / 6 deferred / 2 open)
- `docs/runbooks/security-checklist.md` (operator-deferred items section appended)
