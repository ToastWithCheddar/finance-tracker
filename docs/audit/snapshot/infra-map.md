# Infra snapshot — Docker / nginx / CI / scripts

## docker-compose.yml (the so-called "production" compose)

Despite the unqualified filename, this compose is **dev-mode**:
- `backend` mounts `./backend:/app:cached` and runs `--reload` (`:44-48`). No healthcheck.
- `frontend` builds with `target: dev` (`:61`) and runs `npm run dev` (`:71`). The `production` target in `frontend/Dockerfile` is never reached.
- `ml-worker` mounts `./ml-worker:/app:cached` (`:87`).
- Postgres 5432 and Redis 6379 published to host (`:11, 23-24`) — fine for dev, must not be in prod.
- No `restart: on-failure` deltas, no `mem_limit`/`cpus`, no `deploy.resources`.
- Network: single bridge `finance-network`. No service-internal isolation.
- nginx no healthcheck; depends on backend/frontend without `condition: service_healthy`.
- No log driver, no log rotation.

## docker-compose.dev.yml

26 lines. Adds `DEBUG=true` to backend, re-mounts already-mounted code volumes, re-publishes 5432/6379. Effectively a no-op overlay since base is already dev-mode.

## Dockerfiles

### `backend/Dockerfile`
- Single-stage `python:3.11-slim`.
- Installs `build-essential libpq-dev curl` (`:9-15`) — left in runtime image.
- Non-root `appuser` ✓
- Healthcheck hits `/health` ✓

### `ml-worker/Dockerfile`
- Single-stage. Includes `git` (`:14`).
- Non-root `worker` ✓
- Healthcheck imports the classifier module — re-loads model state every 30s, OOM-kills if model fails to load.
- `CMD celery -A worker worker --loglevel=info --concurrency=2 --max-tasks-per-child=1000`

### `frontend/Dockerfile`
- Multi-stage: `base, deps, dev, builder, production`.
- `production` target broken — `COPY nginx.conf /etc/nginx/conf.d/default.conf` (`:53`) but **`frontend/nginx.conf` does not exist**. Production image build fails.
- `deps` stage unused.
- `dev` stage is what actually runs.

## nginx (`nginx/nginx.conf`, 69 lines)

- `worker_connections 1024`.
- Two upstreams: `backend:8000`, `frontend:3000` (`:6-12`).
- Rate-limit zones: `api 10r/s` (burst 20), `login 5r/m` (burst 5).
- Security headers: `X-Frame-Options DENY`, `X-Content-Type-Options nosniff`, `X-XSS-Protection`, `HSTS` — but HSTS on plain HTTP listener is meaningless.
- WebSocket upgrade headers correctly set on `/ws` (`:58-67`); not on Vite HMR path.
- **No TLS server block** despite compose mapping `:443`. `nginx/ssl/` contains only `README.md`.
- No CSP, no Referrer-Policy, no Permissions-Policy.
- No `proxy_cache`, no static-asset caching, no gzip, no client_max_body_size.

## CI

- `ci.yml` at repo root is **0 bytes**.
- No `.github/workflows/` directory.
- `.github/` contains only `PULL_REQUEST_TEMPLATE.md`.
- `scripts/check.sh:8` runs `python -m py_compile ... || true` and `npm run -s type-check || true` — non-blocking, masks all errors.
- `backend/.pre-commit-config.yaml` exists but no docs/CI run it.

## Scripts (`scripts/`)

- `dev.sh` (1953 B) — copies `.env.example` → `.env` if missing, brings up dev compose, sleeps 10, runs `alembic upgrade head` and seed. Uses legacy `docker-compose` v1 syntax.
- `prod.sh` (307 B) — `docker-compose up --build -d`, sleep 15, ps. **No migrations, no smoke test.**
- `check.sh` — non-blocking lint as above.

## Secrets

- `.env.example` committed with **live-looking** values:
  - `SUPABASE_ANON_KEY` JWT (`:20`)
  - `PLAID_CLIENT_ID` / `PLAID_SECRET` (`:40-42`)
  - `SECRET_KEY=2CWaQcQgzCTj2jOvE4cT5AyiZMsYhi2F` (`:12`)
- Defaults `ENABLE_ADMIN_BYPASS=true`, `CSRF_PROTECTION=false`, `RATE_LIMITING=false` (`.env.example:47-49`) — copy-pasted to prod = wide open.
- Actual `.env` exists at repo root.
- No vault, SOPS, or doppler integration.

## Observability

- No log aggregation (default json-file driver).
- No metrics endpoint anywhere (Prometheus client wired in ml-worker but never started).
- No tracing (no OpenTelemetry, no Jaeger).
- No backup story (postgres volume only; no pg_dump cron, no PITR).

## Production-readiness summary

| Concern | State |
|---|---|
| Healthchecks | postgres ✓, redis ✓, backend ✗ (compose), ml-worker has heavy import-check, nginx ✗ |
| Readiness vs liveness | not distinguished |
| Graceful shutdown | Celery SIGTERM works; backend `--reload` fork-restart not graceful |
| Resource limits | none |
| Restart policy | `unless-stopped` everywhere ✓ |
| Log aggregation | none |
| Metrics | wired in ml-worker code, never started |
| Tracing | none |
| Secret handling | committed `.env`; example contains live creds |
| Backup | postgres volume only |
| TLS | `nginx/ssl/` empty; 443 mapped but no listener |
