# Running the Finance Tracker locally

This is the short, four-step recipe to bring the full stack up on your
machine. For deeper details on individual subsystems (security checklist,
backup, ML model fetch, observability stack, etc.) see the runbooks under
`docs/runbooks/`.

## Prerequisites

- **Docker Desktop** running
- **A real Supabase project** (free tier is fine — see "Supabase setup" below)
- macOS / Linux (Windows works in WSL2; not tested directly)

---

## One-time setup

### 1. Supabase project

The app uses Supabase for authentication. You need a real project for
sign-up / login to work end-to-end (the dev-bypass mode exists but is
gated by environment flags).

1. Sign up at [supabase.com](https://supabase.com), create a new project.
2. **Project Settings → API**: copy these three values:
   - `Project URL` → `SUPABASE_URL`
   - `anon public` key → `SUPABASE_ANON_KEY`
   - `service_role secret` key → `SUPABASE_SERVICE_ROLE_KEY`
3. **Project Settings → Auth → Webhooks** (or **Database → Webhooks**
   depending on dashboard version): set a webhook secret string and copy it
   → `SUPABASE_WEBHOOK_SECRET`.
4. Edit `.env` at the repo root and paste the four values into the matching
   fields. Other keys (`SECRET_KEY`, `ENCRYPTION_KEY_SALT`,
   `PLAID_CLIENT_ID`/`PLAID_SECRET`) already have working dev defaults; you
   only need to fill those in if you want real Plaid linking.

> If you just want to *boot* the stack and click around without real auth,
> set `ENABLE_ADMIN_BYPASS=true`, `ENVIRONMENT=development`, `DEBUG=true`
> in `.env`. Then any request with header
> `Authorization: Bearer dev-mock-token-<anything>` becomes a synthetic
> admin user. **Never enable this in a real deployment.**

### 2. Generate self-signed TLS certs

```bash
make tls-cert
```

This creates `nginx/ssl/{fullchain,privkey}.pem` (gitignored). They're
valid for one year; re-run `make tls-cert` to regenerate.

---

## Boot

```bash
make prod-up
```

This builds the three production Docker images (backend, ml-worker, frontend
— first build takes ~5 min, subsequent runs are instant via cache) and
starts the full stack: nginx (80 + 443), Postgres, Redis, backend FastAPI,
ml-worker Celery, frontend nginx.

Wait ~60 seconds for migrations and the ml-worker to load the MiniLM
model. Then verify:

```bash
curl -k https://localhost/health             # expect {"status":"healthy"}
curl -k https://localhost/api/health          # expect 200 from backend
docker compose -f docker-compose.prod.yml ps  # all containers Up / healthy
```

Open **<https://localhost/>** in your browser. You will see a self-signed
cert warning the first time — accept it (Chrome: "Advanced" → "Proceed";
Safari: "Show Details" → "visit this website").

### First user

On the Login page, click *Sign up*. Supabase emails you a verification
link. Click it, then come back and log in.

---

## Tear down

```bash
make prod-down                # stop containers, keep volumes
make prod-down ARGS=-v        # stop and drop Postgres + Redis volumes
```

---

## Troubleshooting

### "Cannot connect to the Docker daemon"

Docker Desktop isn't running. Start it (`open -a Docker` on macOS) and
wait for the whale icon in the menu bar.

### "port is already allocated" / 80 / 443 / 5432 / 6379

Something else on your machine is using those ports. Either stop the
other process (`lsof -i :443` to find it) or edit `docker-compose.prod.yml`
to map different host ports.

### Backend container restarts in a loop

Most likely cause: a missing required env var in `.env` (e.g. you skipped
the Supabase keys). Check logs:

```bash
docker compose -f docker-compose.prod.yml logs backend --tail=60
```

If you see `RuntimeError: SUPABASE_URL is required` or similar, fill in
the missing key in `.env` and `make prod-down && make prod-up`.

### Backend logs show "Alembic config check failed"

The Alembic migration head couldn't be reached. This usually means the
Postgres container is still booting. Wait 30s and re-check; if it
persists, drop the volume and try again:

```bash
make prod-down ARGS=-v
make prod-up
```

### ml-worker container is "Up" but `/ready` returns 503

The MiniLM model is still loading on first boot (~30s on Apple Silicon,
~60s on x86). Check `docker compose ... logs ml-worker --tail=40` — if you
see `loading model`, just wait. If you see `Model not found`, run
`bash ml-worker/scripts/fetch_models.sh` to pull the weights.

### Browser shows "ERR_SSL_PROTOCOL_ERROR" or "Connection refused"

You didn't run `make tls-cert` (no `nginx/ssl/*.pem` files exist), or
nginx didn't pick them up. Check `docker compose ... logs nginx --tail=20`.
Re-run `make tls-cert && make prod-down && make prod-up`.

### Tests fail / I want to run the tests

- Backend pytest (real Postgres + Redis via testcontainers):
  ```bash
  cd backend && .venv/bin/pytest tests/ -q
  ```
- Frontend Vitest:
  ```bash
  cd frontend && npm test
  ```
- ml-worker pytest (offline, with `ML_AUDIT_SKIP_MODEL=1` for fast runs):
  ```bash
  cd ml-worker && ML_AUDIT_SKIP_MODEL=1 .venv/bin/pytest tests/unit/ -q
  ```

Live counts as of 2026-05-08: backend 40 passing / 0 failing / 10 xfailed,
frontend 68 passing / 0 failing / 2 skipped, ml-worker 52 passing.

---

## What lives where

| Concern | Path |
|---|---|
| End-of-phase Turkish report | `REPORT.md` |
| Risk register (CSV) | `docs/audit/findings.csv` |
| Per-wave changelogs | `docs/integration/{01..13}-*.md` |
| Runbooks | `docs/runbooks/*.md` |
| Mermaid diagrams | `docs/audit/diagrams/*.md` |
| Before/after metrics | `docs/audit/metrics/{baseline,improved,runtime}.md` |

For deployment to a real cloud (TLS via Let's Encrypt, S3 backups,
production-grade Supabase RLS policies), see
`docs/runbooks/security-checklist.md` "Operator-deferred items".
