# CI + Makefile runbook

Orchestrates the test pyramid (`backend/`, `frontend/`, `ml-worker/`, `e2e/`),
benchmarks (`benchmarks/`), and the production / observability docker-compose
stacks. Promoted to `docs/runbooks/` by IW-2.

```
.github/workflows/ci.yml          # GitHub Actions; promoted from audit.yml
Makefile                          # repo-root orchestrator (install-*, test-*, bench-*, prod-*, lint, clean, e2e)
docker-compose.prod.yml           # production stack (INFRA-DOCK-002)
docker-compose.observability.yml  # optional Prom/Grafana/Loki/Promtail/OTel add-on (INFRA-OBS-001/002)
docs/runbooks/ci-makefile.md      # this file
```

## Production stack (Section D)

`docker-compose.prod.yml` is the standalone production overlay. It does NOT
inherit from the repo-root `docker-compose.yml` (which is dev-only); bring it
up directly:

```bash
make prod-config-check    # validate (no daemon needed)
make prod-up              # build prod targets and start
make prod-down ARGS="-v"  # stop and drop volumes
```

Layer observability on top:

```bash
docker compose \
  -f docker-compose.prod.yml \
  -f docker-compose.observability.yml \
  up -d
```

Backup / restore:

```bash
BACKUP_BUCKET=ft-backups make backup
BACKUP_BUCKET=ft-backups KEY=postgres/2026/04/27/finance-...sql.gz \
  make restore
```

See `docs/runbooks/{backup,tls-options,model-fetch}.md` for operator
procedures.

## Makefile

All targets resolve paths via `MAKEFILE_DIR` and work from any cwd. Invoke from repo root:

```bash
make help
```

### Install

| Target | Action |
|---|---|
| `install-backend` | `python -m venv` in `backend/` + `pip install -e backend[dev]` (test deps live in the `dev` extra). |
| `install-frontend` | `npm ci` in `frontend/`. |
| `install-ml-worker` | venv + `pip install -e .` in `ml-worker/tests`. |
| `install-bench-backend` | venv + `pip install -e .` in `benchmarks/backend`. |
| `install-bench-frontend` | `npm ci` in `benchmarks/frontend`. |
| `install-all` | All five above, sequentially. |

### Test

| Target | Notes |
|---|---|
| `test-backend` | Runs `pytest` in `backend/`. Requires Docker (testcontainers spins Postgres 15 + Redis 7). |
| `test-frontend` | Runs `npm test` (Vitest) in `frontend/`. |
| `test-ml-worker` | Runs `pytest` in `ml-worker/tests`. Set `ML_AUDIT_SKIP_MODEL=1` to skip the 90MB MiniLM load. |
| `test-all` | Runs the three above. e2e is **not** included — Playwright requires a live stack. |
| `e2e` | Runs `npm test` in `e2e/`. Pre-conditions: `cd e2e && npm install && npx playwright install`, plus a running app stack the Playwright config can hit. |

### Bench

| Target | Pre-conditions |
|---|---|
| `bench-backend` | The full app stack must already be running and reachable at `BENCH_HOST` (default `http://localhost:8000`). The script does **not** start services. |
| `bench-frontend` | `frontend/dist/` must exist (run `npm run build` in `frontend/` first). |
| `bench-all` | Both. Pre-conditions of each apply. |

### Quality

| Target | Notes |
|---|---|
| `lint` | `ruff check` over `backend/tests` + `ml-worker/tests`; `npm run lint` in `frontend/` if a `lint` script is defined. Missing tools degrade to non-fatal placeholders. |
| `clean` | Removes `.venv/`, `node_modules/`, `__pycache__/`, `.pytest_cache/` under the test/bench directories. |

### Help

`help` is the default target.

## GitHub Actions workflow

`.github/workflows/ci.yml` runs the matrix on every push, pull request, and
manual dispatch. Jobs:

- `backend-test` — Postgres 15 + Redis 7 service containers with health checks; Python 3.11; `make install-backend` then `make test-backend`.
- `frontend-test` — Node 20; `make install-frontend` + `make test-frontend`.
- `ml-worker-test` — Python 3.11 with `ML_AUDIT_SKIP_MODEL=1` so the 90 MB safetensors download is skipped in CI; LRU and confidence-bucket tests still run.
- `bench-frontend-build-check` — Node 20; builds `frontend/` and runs the bundle analyzer (`npm run analyze:bundle`). Lighthouse is deferred (Chrome setup will land in a later wave).
- `security-scan` — `pip-audit` on `backend/requirements.txt`, `npm audit` on `frontend/`, and a Trivy filesystem scan. Non-blocking (`continue-on-error: true`) to establish a baseline.

Top-level config:
- `name: ci`
- `on: [push, pull_request, workflow_dispatch]`
- `concurrency: { group: ci-${{ github.ref }}, cancel-in-progress: true }`
- All actions pinned to major versions (`@v4`, `@v5`).
- Jobs are independent; one failing job does not cancel the others.

## Promotion checklist

Before relying on this workflow to gate PRs:

1. `make install-all` succeeds locally.
2. `make test-all` is green (Docker daemon running).
3. `make bench-frontend` runs cleanly against a `frontend/dist/` build.
4. `make e2e` is green against a live stack (Playwright browsers installed).
5. `security-scan` baseline report is reviewed and triaged into the findings spreadsheet.
