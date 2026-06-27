# IW-4 — Runbooks & Audit Historical Docs

## Summary

Pure relocation wave. Moved operational runbooks from `audit/70-runbooks/` to `docs/runbooks/`, and moved audit history (snapshot, findings register, improvement-section briefs, original audit README) to `docs/audit/`. Rewrote stale `audit/<NN>-...` cross-references inside the moved markdown/CSV files to point at the canonical post-integration locations. Added fresh `README.md` index files for both `docs/audit/` and `docs/runbooks/`.

No code or behavior changes. No deletions of canonical sources. Source files under `audit/` were not under git tracking, so plain `mv` was used (equivalent semantics — IW-6 owns the eventual `audit/` parent removal).

## Files moved

| From | To |
|---|---|
| `audit/70-runbooks/backup.md` | `docs/runbooks/backup.md` |
| `audit/70-runbooks/tls-options.md` | `docs/runbooks/tls-options.md` |
| `audit/70-runbooks/model-fetch.md` | `docs/runbooks/model-fetch.md` |
| `audit/70-runbooks/csrf-strategy.md` | `docs/runbooks/csrf-strategy.md` |
| `audit/70-runbooks/encryption-migration.md` | `docs/runbooks/encryption-migration.md` |
| `audit/70-runbooks/security-checklist.md` | `docs/runbooks/security-checklist.md` |
| `audit/00-snapshot/` | `docs/audit/snapshot/` |
| `audit/10-findings/findings.csv` | `docs/audit/findings.csv` |
| `audit/10-findings/findings-detail.md` | `docs/audit/findings-detail.md` |
| `audit/20-improvement-sections/` | `docs/audit/improvement-sections/` |
| `audit/README.md` | `docs/audit/AUDIT_OVERVIEW.md` |

## Files deleted

- `audit/70-runbooks/README.md` — placeholder index, superseded by the new `docs/runbooks/README.md`. Content was a forward-looking list of expected runbooks; not preserved verbatim.

## Files edited

- All `*.md` and `*.csv` under `docs/audit/` and `docs/runbooks/` were rewritten via `perl -i -pe` to replace `audit/(00-|10-|20-|30-|40-|50-|60-|70-)…` paths with their canonical homes:
  - `audit/30-tests/{backend,frontend,ml-worker}` → `{backend,frontend,ml-worker}/tests`
  - `audit/30-tests/e2e` → `e2e`
  - `audit/40-benchmarks` → `benchmarks`
  - `audit/50-logging/{otel,grafana}` → `ops/observability/{otel,grafana}`
  - `audit/50-logging/structlog_config.py` → `backend/app/core/logging_config.py`
  - `audit/50-logging/frontend/logger.ts` → `frontend/src/lib/logger.ts`
  - `audit/60-ci/workflows/audit.yml` → `.github/workflows/ci.yml`
  - `audit/60-ci/Makefile` → `Makefile`
  - `audit/60-ci/docker-compose.prod.yml` → `docker-compose.prod.yml`
  - `audit/60-ci/docker-compose.observability.yml` → `docker-compose.observability.yml`
  - `audit/60-ci/compose.test.yml` → `docker-compose.test.yml`
  - `audit/60-ci/Dockerfile.backend.prod` → `backend/Dockerfile.prod`
  - `audit/60-ci/Dockerfile.ml-worker.prod` → `ml-worker/Dockerfile.prod`
  - `audit/70-runbooks/X.md` → `docs/runbooks/X.md`
  - `audit/10-findings/findings.csv` → `docs/audit/findings.csv`
  - `audit/00-snapshot/...` → `docs/audit/snapshot/...`
  - `audit/20-improvement-sections/...` → `docs/audit/improvement-sections/...`

## Files added

- `docs/audit/README.md` — entry point for the audit archive.
- `docs/runbooks/README.md` — index of operational runbooks with one-line descriptions.
- `docs/integration/04-runbooks-and-docs.md` — this changelog.

## Verification

- `find docs -type f -name '*.md' -o -name '*.csv' | xargs grep -lE "audit/(00-|10-|20-|30-|40-|50-|60-|70-)"` returns empty (no stale paths in moved docs).
- `python3 -c "import csv; list(csv.reader(open('docs/audit/findings.csv')))"` parses cleanly.
- `wc -l docs/audit/findings.csv` → 79 lines (matches pre-move count).
- All moved runbook files are present under `docs/runbooks/` alongside `observability-stack.md` produced by IW-3.

## Open follow-ups

- IW-2 promotes the CI workflow which currently has `audit/*` paths to rewrite — that's IW-2's responsibility, not this wave's.
- The `audit/` parent directory still exists with residual subdirectories (`30-tests/`, `40-benchmarks/`, `50-logging/`, `60-ci/`, and emptied `10-findings/`, `70-runbooks/`). IW-6 owns final removal of the parent once all sibling waves have moved their owned content.
