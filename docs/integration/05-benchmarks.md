# IW-5 — Benchmarks promoted to top-level `benchmarks/`

## Summary
Moved the audit performance harnesses out of `audit/40-benchmarks/` and into
a top-level `benchmarks/` directory. The contents (Locust + microbench for
backend, Lighthouse CI + bundle analyzer + Playwright trace for frontend)
are unchanged; only paths and the dedicated `.gitignore` retention rules
were rewritten. The Makefile target rename and CI workflow update are
explicitly deferred to IW-2.

## Files moved
| Source | Destination | Notes |
|---|---|---|
| `audit/40-benchmarks/backend/` | `benchmarks/backend/` | locust + microbench harness |
| `audit/40-benchmarks/frontend/` | `benchmarks/frontend/` | LHCI + bundle analyzer + Playwright |
| `audit/40-benchmarks/README.md` | `benchmarks/README.md` | top-level overview |

(Sources were untracked in git, so plain `mv` was used; `git mv` errored
with "source directory is empty" because there was no index entry to move.)

## Files added
- `benchmarks/.gitignore` — folds the bench-specific retention rules from
  `audit/.gitignore`, with the `40-benchmarks/` prefix stripped:
  ```
  **/.venv/
  **/node_modules/
  **/__pycache__/
  **/*.egg-info/
  **/.pytest_cache/
  **/.vitest-cache/
  **/coverage/
  **/.coverage
  **/htmlcov/
  **/reports/*
  !**/reports/.gitkeep
  !**/reports/baseline.json
  backend/reports/requests_raw.csv
  backend/reports/percentiles.csv
  ```

## Files edited (path rewrites only)
- `audit/.gitignore` — removed the bench reports retention block (now lives
  in `benchmarks/.gitignore`).
- `benchmarks/backend/README.md` — `audit/40-benchmarks/backend/` → `benchmarks/backend/` (3 occurrences).
- `benchmarks/frontend/README.md` — `audit/40-benchmarks/frontend` → `benchmarks/frontend` (2 occurrences); `cd ../../../frontend` → `cd ../../frontend` (one less hop).
- `benchmarks/frontend/lighthouserc.cjs` — `FRONTEND_DIR` resolves with one fewer `..` hop.
- `benchmarks/frontend/scripts/analyze_bundle.mjs` — same `FRONTEND_DIR` fix; doc comment updated.
- `benchmarks/frontend/scripts/render_trace.mjs` — same `FRONTEND_DIR` fix; doc comment updated.
- `benchmarks/frontend/scripts/capture_baseline.sh` — `REPO_ROOT="$(cd "${HARNESS_DIR}/../../.." && pwd)"` → `${HARNESS_DIR}/../..`.
- `benchmarks/frontend/playwright/playwright.config.ts` — `FRONTEND_DIR` lost one `..` (now `__dirname` + 3 hops to repo root + `frontend`).

## Verification
```
$ grep -rn "audit/40-benchmarks\|audit/30-tests\|audit/60-ci" benchmarks
(no matches)

$ cd benchmarks/frontend && npx tsc --noEmit -p tsconfig.json
(exit 0, no diagnostics)

$ bash -n benchmarks/frontend/scripts/capture_baseline.sh
(clean)

$ bash -n benchmarks/backend/scripts/capture_baseline.sh
(clean)

$ python3 -c "import sys; sys.path.insert(0, 'benchmarks/backend'); import locust.locustfile"
ImportError: cannot import name 'HttpUser' from 'locust' (unknown location)
# expected: locust pkg not installed in this Python; the local `locust/`
# pkg shadows it. The locustfile *file* was found and loaded — the failure
# is on its own `from locust import HttpUser`. Acceptable per IW-5 brief.
```

(Two README references to `audit/10-findings/findings.csv` and
`audit/20-improvement-sections/A-performance.md` remain in
`benchmarks/backend/README.md`. These are documentation pointers to audit
artifacts owned by IW-6, not path-dependent imports, and the IW-5 grep
scope explicitly only flagged `audit/40-benchmarks`, `audit/30-tests`, and
`audit/60-ci`. Left as-is for IW-6 to decide whether to drop or rewrite
when the audit tree is removed.)

## Open follow-ups (for IW-2)
1. **Makefile target renames** — rename and re-point cwd to `benchmarks/...`:
   - `audit-bench-be-baseline` → `bench-be-baseline`
   - `audit-bench-be-smoke` → `bench-be-smoke`
   - `audit-bench-be-microbench` → `bench-be-microbench`
   - `audit-bench-fe-baseline` → `bench-fe-baseline`
   - `audit-bench-fe-lhci` → `bench-fe-lhci`
   - `audit-bench-fe-bundle` → `bench-fe-bundle`
   - `audit-bench-fe-trace` → `bench-fe-trace`
   - `audit-bench-fe-typecheck` → `bench-fe-typecheck`
   - any aggregate `audit-bench` → `bench`
   (Inspect actual Makefile for the canonical list; the above is the
   expected naming scheme — IW-2 should reconcile.)
2. **CI workflow** — the `bench-frontend-build-check` job's
   `working-directory:` (and any path filters) must point at
   `benchmarks/frontend` instead of `audit/40-benchmarks/frontend`.

## Owner / out-of-scope
- IW-6 owns deletion of `audit/40-benchmarks/` (now empty) and the rest of
  `audit/`.
- IW-2 owns Makefile + CI updates (above).
