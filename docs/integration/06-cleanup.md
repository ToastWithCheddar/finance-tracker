# Integration Wave 6 — Final cleanup (stale-ref sweep + audit/ deletion)

**Date:** 2026-04-27
**Agent:** IW-6 (Opus 4.7, medium-effort)
**Scope:** Sweep all remaining `audit/(00-..70-)` references in the repo
(excluding historical changelogs under `docs/integration/`), rewrite each to
its canonical post-integration path, then delete the now-orphan `audit/`
directory.

---

## 1. Stale-reference sweep — before / after

### BEFORE — 27 stale references in 18 files (excluding `docs/integration/` and `audit/`)

| File | Count |
|---|---|
| `frontend/src/utils/logger.ts` | 1 |
| `frontend/src/services/csrf.ts` | 1 |
| `Makefile` | 1 |
| `backend/migrations/versions/a1b2c3d4e5f6_audit_catchup_indexes.py` | 1 |
| `backend/app/logging_config.py` | 2 |
| `backend/app/services/encryption_migration.py` | 2 |
| `backend/tests/README.md` | 2 |
| `docs/runbooks/ci-makefile.md` | 1 |
| `nginx/nginx.conf` | 1 |
| `benchmarks/backend/README.md` | 2 |
| `benchmarks/README.md` | 1 |
| `.github/workflows/ci.yml` | 1 (provenance — preserved) |
| `e2e/playwright.config.ts` | 1 |
| `ml-worker/app/logging_config.py` | 2 |
| `ml-worker/tests/unit/test_lru_cache_proposal.py` | 1 |
| `ml-worker/tests/helpers/confidence.py` | 2 |
| `ml-worker/tests/helpers/__init__.py` | 1 |
| `ml-worker/ml_classification_service.py` | 2 |
| `ml-worker/scripts/fetch_models.sh` | 1 |
| **TOTAL** | **26 rewrites + 1 preserved provenance** |

By extension:
- `.py`: 14 rewrites (across 8 files)
- `.md`: 6 rewrites (across 4 files)
- `.ts`: 3 rewrites (across 3 files)
- `Makefile`: 1
- `.conf`: 1
- `.sh`: 1

### AFTER — single intentional match

```
.github/workflows/ci.yml:3:# Promoted from audit/60-ci/workflows/audit.yml by IW-2. All targets dispatch
```

This single line is a deliberate provenance comment kept by IW-2's plan.
Everything else is gone.

---

## 2. Path rewrites applied

Per the plan's mapping table:

- `audit/30-tests/ml-worker/helpers/confidence.py` → `ml-worker/tests/helpers/confidence.py`
- `audit/00-snapshot/ml-worker-map.md` → `docs/audit/snapshot/ml-worker-map.md`
- `audit/10-findings/findings.csv` → `docs/audit/findings.csv`
- `audit/20-improvement-sections/{A,B,F}-*.md` → `docs/audit/improvement-sections/{A,B,F}-*.md`
- `audit/50-logging/structlog_config.py` → docstring rewritten in
  `backend/app/logging_config.py` and `ml-worker/app/logging_config.py` (these
  ARE canonical now; the W5 docstring was inverted)
- `audit/50-logging/frontend/logger.ts` → header in `frontend/src/utils/logger.ts`
  rewritten (no longer claims an external canonical source)
- `audit/50-logging/README.md` → `docs/runbooks/observability-stack.md`
- `audit/60-ci/Makefile` provenance line in `Makefile` shortened
- `audit/60-ci/README.md` provenance in `docs/runbooks/ci-makefile.md` shortened
- `audit/70-runbooks/{csrf-strategy,encryption-migration,tls-options,model-fetch}.md`
  → `docs/runbooks/{csrf-strategy,encryption-migration,tls-options,model-fetch}.md`

The one preserved reference (`.github/workflows/ci.yml:3`) is provenance — a
useful one-liner that lets future readers trace `ci.yml` back to its
`audit/60-ci/workflows/audit.yml` origin.

---

## 3. `audit/` deletion

State before deletion (file counts by sub-directory):

| Sub-directory | Tracked? | Files |
|---|---|---|
| `audit/00-snapshot/` | n/a | 0 |
| `audit/10-findings/` | n/a | 0 |
| `audit/20-improvement-sections/` | n/a | 0 |
| `audit/30-tests/` | untracked | **41,405** (almost entirely an in-tree `.venv` and `node_modules` from prior agent runs) |
| `audit/40-benchmarks/` | n/a | 0 |
| `audit/50-logging/` | n/a | 0 |
| `audit/60-ci/` | n/a | 0 |
| `audit/70-runbooks/` | n/a | 0 |
| **TOTAL** | — | **41,406** |

`git ls-files audit/` returned **0 tracked files**, so a plain `rm -rf audit/`
was sufficient — no `git rm` needed, nothing to stage. The 41,405 files in
`audit/30-tests/` were all from `.venv/` (sentence-transformers, torch, etc.)
and `node_modules/` left over by IW-1 — none of it was source. The
`audit/30-tests/{frontend/{package.json, README.md}, README.md, e2e/playwright-report/index.html}`
README/manifest leftovers were also captured in the same sweep.

Verification:

```
$ test ! -e audit && echo "audit/ deleted"
audit/ deleted
```

---

## 4. MEMORY changes

- Deleted `feedback_modular_audit_folder.md`.
- Created `feedback_integration_complete.md` documenting that the modular
  rule is retired (2026-04-27) and listing the canonical destinations.
- Updated `MEMORY.md` index: replaced the `feedback_modular_audit_folder.md`
  bullet with a `feedback_integration_complete.md` bullet.

---

## 5. Open follow-ups

Only IW-7 (final repo-wide verification — rerun pytest/playwright smoke,
confirm the CI workflow loads, sanity-check `make` targets resolve from repo
root). No outstanding rewrites.

---

## 6. Final repo-root listing (post-cleanup)

```
.github/  Makefile  backend/  benchmarks/  docker-compose.{dev,prod,observability,*}.yml
docs/  e2e/  frontend/  ml-worker/  ml_models/  nginx/  ops/  scripts/
```

No `audit/` directory. No stale `audit/(00-..70-)` paths anywhere outside
`.github/workflows/ci.yml:3` (intentional provenance) and
`docs/integration/*.md` (historical changelogs, preserved verbatim per plan).
