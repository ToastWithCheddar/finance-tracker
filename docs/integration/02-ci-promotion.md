# IW-2 — CI promotion (workflow, Makefile, prod compose)

## Summary
Promoted `audit/60-ci/*` to canonical homes: the GitHub Actions workflow now lives at `.github/workflows/ci.yml` (renamed from `audit.yml`), the orchestrator Makefile sits at the repo root, and the production / observability compose files sit at the repo root next to the existing dev `docker-compose.yml`. The 0-byte `ci.yml` placeholder at the repo root (left over from the original internship) was removed. The audit subtree's CI README was relocated to `docs/runbooks/ci-makefile.md`. All `audit/30-tests/*`, `audit/40-benchmarks/*`, and `audit/60-ci/*` path references inside these files were rewritten to canonical homes (`backend/`, `frontend/`, `ml-worker/`, `e2e/`, `benchmarks/backend/`, `benchmarks/frontend/`). All Makefile targets were renamed to drop the `audit-` prefix; CI invocations were updated to match. No CI logic, no compose service definitions, no recipe semantics changed beyond path/target rewrites and the addition of an `e2e` Make target.

## Files moved
| Source | Destination | Notes |
|---|---|---|
| audit/60-ci/workflows/audit.yml | .github/workflows/ci.yml | renamed at the same time; `name: audit` → `name: ci` |
| audit/60-ci/Makefile | Makefile | repo-root orchestrator; `MAKEFILE_DIR` auto-adapts |
| audit/60-ci/docker-compose.prod.yml | docker-compose.prod.yml | sibling of dev compose |
| audit/60-ci/docker-compose.observability.yml | docker-compose.observability.yml | IW-3's `./ops/observability/...` mount edits preserved |
| audit/60-ci/README.md | docs/runbooks/ci-makefile.md | promotion checklist + Makefile target reference |

## Files deleted
- `ci.yml` (repo root, 0-byte placeholder from the original internship — superseded by `.github/workflows/ci.yml`)

## Makefile target renames
| Old (audit-prefixed) | New (canonical) |
|---|---|
| audit-install-backend | install-backend |
| audit-install-frontend | install-frontend |
| audit-install-ml-worker | install-ml-worker |
| audit-install-bench-backend | install-bench-backend |
| audit-install-bench-frontend | install-bench-frontend |
| audit-install-all | install-all |
| audit-test-backend | test-backend |
| audit-test-frontend | test-frontend |
| audit-test-ml-worker | test-ml-worker |
| audit-test-all | test-all |
| audit-bench-backend | bench-backend |
| audit-bench-frontend | bench-frontend |
| audit-bench-all | bench-all |
| audit-lint | lint |
| audit-clean | clean |
| audit-prod-config-check | prod-config-check |
| audit-prod-up | prod-up |
| audit-prod-down | prod-down |
| audit-backup | backup |
| audit-restore | restore |
| _new_ | e2e (Playwright; requires running stack + `npm install` + `npx playwright install`) |

`test-all` depends on `test-backend test-frontend test-ml-worker`. `e2e` is intentionally NOT a dep of `test-all` — Playwright requires the prod-or-dev stack to be live.

## Workflow path rewrites (`.github/workflows/ci.yml`)
| Old | New |
|---|---|
| `name: audit` | `name: ci` |
| `audit-${{ github.ref }}` (concurrency group) | `ci-${{ github.ref }}` |
| `make -f audit/60-ci/Makefile audit-install-backend` | `make install-backend` |
| `make -f audit/60-ci/Makefile audit-test-backend` | `make test-backend` |
| `make -f audit/60-ci/Makefile audit-install-frontend` | `make install-frontend` |
| `make -f audit/60-ci/Makefile audit-test-frontend` | `make test-frontend` |
| `make -f audit/60-ci/Makefile audit-install-ml-worker` | `make install-ml-worker` |
| `make -f audit/60-ci/Makefile audit-test-ml-worker` | `make test-ml-worker` |
| `make -f audit/60-ci/Makefile audit-install-bench-frontend` | `make install-bench-frontend` |
| `cache-dependency-path: audit/30-tests/frontend/package-lock.json` | `cache-dependency-path: frontend/package-lock.json` |
| `working-directory: audit/40-benchmarks/frontend` | `working-directory: benchmarks/frontend` |

The `pip install -e backend/` step in CI is unchanged (folded into `make install-backend`, which now installs `-e backend[dev]` from `backend/pyproject.toml` since IW-1's fold consolidated the test deps under the `dev` extra; backend has no separate `test` extra).

## docker-compose.prod.yml path rewrites
Build contexts and bind-mount paths walked one directory up: `../../backend` → `./backend`, `../../frontend` → `./frontend`, `../../ml-worker` → `./ml-worker`, `../../.env` → `./.env`, `../../backend/init.sql` → `./backend/init.sql`. Per IW-4, the nginx mounts already pointed at `./frontend/nginx.conf` / `./frontend/nginx/ssl` — verified, no further edits needed there. Service definitions, healthchecks, resource limits, and the commented Loki/Promtail block are unchanged.

## docker-compose.observability.yml
IW-3 already rewrote bind mounts to `./ops/observability/...`. Verified post-move; no edits required.

## Validation
- `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` — parses.
- `python3 -c "import yaml; yaml.safe_load(open('docker-compose.prod.yml'))"` — parses.
- `python3 -c "import yaml; yaml.safe_load(open('docker-compose.observability.yml'))"` — parses.
- `make -n help` — lists renamed targets.
- `grep -rn "audit/30-tests\|audit/40-benchmarks\|audit/60-ci\|audit-test-\|audit-install-\|audit-bench-\|audit-prod-" .github Makefile docker-compose.prod.yml docker-compose.observability.yml docs/runbooks/ci-makefile.md` returns empty (excluding `docs/integration/`).
- `test ! -e ci.yml` — the 0-byte placeholder is gone.

## Open follow-ups
- **IW-6** owns the deletion of `audit/60-ci/` (and the rest of `audit/`). Do not delete in this wave.
- **Promotion checklist**: complete the items in `docs/runbooks/ci-makefile.md` (run `make install-all`, `make test-all` locally with Docker, run `make bench-frontend` against a built `frontend/dist/`, and triage the `security-scan` baseline) before relying on the new `.github/workflows/ci.yml` to gate PRs.
