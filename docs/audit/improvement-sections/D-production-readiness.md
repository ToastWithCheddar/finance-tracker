# Section D — Production Readiness

**Owner agent:** Opus 4.7, medium effort.

## Scope

Findings: BE-PR-001..006, FE-PR-001..005, FE-SEC-003, ML-PR-005, INFRA-CI-001..002, INFRA-DOCK-001..005, INFRA-NGINX-001, INFRA-BACKUP-001.

## Tasks

### Docker

1. **Author `docker-compose.prod.yml`**:
   - No code mounts.
   - `backend`: gunicorn + uvicorn workers, `target: prod` from new multi-stage Dockerfile.
   - `frontend`: nginx serving build artifacts (use new `frontend/nginx.conf`).
   - `ml-worker`: same image as today but `--without-mingle --without-gossip` for faster start.
   - Postgres + Redis NOT exposed to host.
   - `mem_limit`/`cpus` per service.
   - `logging.driver: "json-file"` with rotation `max-size: 10m, max-file: 3`.

2. **Multi-stage backend Dockerfile**:
   ```dockerfile
   FROM python:3.11-slim AS builder
   RUN apt-get install -y --no-install-recommends build-essential libpq-dev
   COPY requirements-prod.txt .
   RUN pip install --user -r requirements-prod.txt

   FROM python:3.11-slim AS runtime
   RUN apt-get install -y --no-install-recommends libpq5 curl && rm -rf /var/lib/apt/lists/*
   COPY --from=builder /root/.local /home/appuser/.local
   USER appuser
   ENV PATH=/home/appuser/.local/bin:$PATH
   COPY app /app/app
   HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1
   CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "4", "app.main:app"]
   ```

3. **Multi-stage ml-worker Dockerfile**: drop `git`; runtime stage without compilers; do not bake model weights — fetch at startup from S3 or volume mount.

4. **Fix frontend prod build (INFRA-DOCK-001)**:
   - Add `frontend/nginx.conf`:
     ```nginx
     server {
       listen 80;
       root /usr/share/nginx/html;
       gzip on; gzip_types text/css application/javascript application/json;
       location ~* \.(js|css|woff2?|svg|png)$ { expires 1y; add_header Cache-Control "public, immutable"; }
       location / { try_files $uri /index.html; }
     }
     ```

5. **Remove model weights from Git (ML-PR-005)**:
   - `git rm -r ml_models/ ml-worker/models/ ml-worker/model_cache/`.
   - Add to `.gitignore`.
   - Document fetch at `docs/runbooks/model-fetch.md`.
   - Add `ml-worker/scripts/fetch_models.sh` that pulls from S3 (or HF Hub as a fallback).

6. **`.dockerignore` updates**:
   - `ml-worker/.dockerignore`: add `models/`, `model_cache/`, `ab_test_results/`.
   - `backend/.dockerignore`: add `tests/`, `__pycache__`, `*.pyc`.
   - `frontend/.dockerignore`: add `node_modules`, `dist`, `coverage`.

### Nginx (handoff for INFRA-NGINX-001)

- Add a 443 server block with `listen 443 ssl http2`.
- Move HSTS header to 443 only.
- Document Caddy as a simpler alternative in `docs/runbooks/tls-options.md`.
- Recommend `acme-companion` for Let's Encrypt automation in compose.

### Migrations (BE-PR-001, BE-PR-002)

- Author Alembic revisions catching up to current `Base.metadata`. Run `alembic revision --autogenerate -m "catchup_audit_baseline"` and review carefully.
- Remove `Base.metadata.create_all` from `app/main.py:66`.
- Add CI check: `alembic check` (or custom script comparing autogenerate to empty diff).

### Auth shape mismatch (FE-SEC-003)

Pick `tokens.access_token` snake_case (matches backend Pydantic). Update `frontend/src/services/api.ts:309-336` to read snake_case. Update `authStore.register` similarly. Confirm with the auth flow Vitest tests.

### CI workflow (INFRA-CI-001)

`.github/workflows/ci.yml`:
```yaml
name: audit
on: [push, pull_request]
jobs:
  backend:
    runs-on: ubuntu-latest
    services: { postgres: {...}, redis: {...} }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install -r backend/requirements.txt -r backend/tests/requirements.txt
      - run: ruff check backend backend/tests
      - run: mypy backend/app
      - run: pytest backend/tests --cov=backend/app
  frontend:
    steps: [setup-node, npm ci, npm run lint, vitest run --coverage]
  e2e:
    steps: [docker compose -f docker-compose.test.yml up -d, npx playwright test]
  security:
    steps: [pip-audit, npm audit, trivy image scan]
```

Move into `.github/workflows/audit.yml` once green.

### Cleanup duplicates

- Pick `app/scripts/seed_data.py`, delete `app/seed_data.py` (BE-PR-003).
- Pick `app/database.py`, delete `app/database_manager.py` (BE-PR-004).
- Fix uvicorn log_level call (BE-PR-005).

### Frontend strict TS / a11y

- Enable ESLint rule `@typescript-eslint/no-explicit-any: error`. Codemod fixes per file.
- Add `eslint-plugin-jsx-a11y` recommended preset.
- Centralize hard-coded localhost URLs behind strict env validation (FE-PR-003).

### Backup (INFRA-BACKUP-001)

`docs/runbooks/backup.md`:
- Cron container running `pg_dump | gzip | aws s3 cp - s3://...`.
- Retention: 30 daily + 12 monthly via S3 lifecycle.
- Restore drill checklist.

## Deliverables

- `docker-compose.prod.yml`
- `backend/Dockerfile.prod`
- `ml-worker/Dockerfile.prod`
- `frontend/nginx.conf` (in internship tree because Dockerfile expects it there)
- `.github/workflows/ci.yml`
- `docs/runbooks/{backup,tls-options,model-fetch}.md`
- Alembic catchup migration in `backend/migrations/versions/`
- ESLint config updates in `frontend/eslint.config.js`

## Success metrics

- `docker build` succeeds on every Dockerfile (incl. frontend production target).
- `docker compose -f docker-compose.prod.yml up` brings up a healthy stack.
- `git ls-files | xargs -I{} du -b {} | awk '{s+=$1} END {print s}'` drops by >250 MB.
- `audit.yml` runs green on PR.
- One full restore-from-backup test executed and documented.

## Agent prompt template

> Finance-tracker production-readiness work. Opus 4.7 medium effort. Read `docs/audit/improvement-sections/D-production-readiness.md`. Author all deliverables; modify internship code at the integration points listed. Validate by running `docker build` for each Dockerfile and `docker compose -f docker-compose.prod.yml config`. Update findings.csv.
