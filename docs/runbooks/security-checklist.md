# Pre-deploy security checklist

Run this before every promotion to staging or production. Each item maps to
a closed finding so regressions are easy to diagnose.

## Configuration gates

- [ ] `RATE_LIMITING=true` (BE-RL-001) — login `10/min`, register `3/hour`,
      password-reset `3/hour`, `/transactions/export` `5/min`.
- [ ] `CSRF_PROTECTION=true` (FE-SEC-002 / BE-SEC-005).
- [ ] `ENABLE_ADMIN_BYPASS=false` (BE-SEC-002 / BE-SEC-005). Verified via
      `backend/tests/security/test_dev_bypass_disabled_in_prod.py`.
- [ ] `ENVIRONMENT=production` and `DEBUG=false`.
- [ ] `SECRET_KEY` set, ≥32 chars, NOT the placeholder from `.env.example`.
- [ ] `ENCRYPTION_KEY_SALT` set, 64 hex chars (BE-SEC-003).
- [ ] `PLAID_BASE_URL` resolves correctly for the target environment
      (BE-SEC-006). Default derived from `PLAID_ENV`.
- [ ] `SUPABASE_WEBHOOK_SECRET` set and rotated since last incident.

## Secrets hygiene

- [ ] `.env.example` contains no live credentials (BE-SEC-004 — covered).
- [ ] `git log -p -- .env.example` shows no rotation regressions.
- [ ] All real secrets live in the secret manager, not in repo or images.

## Transport / TLS

- [ ] HTTPS terminator (nginx) configured with valid certs (INFRA-NGINX-001).
- [ ] HSTS header only on the 443 server block.

## CSP / headers

- [ ] CSP, Referrer-Policy, Permissions-Policy headers present
      (INFRA-NGINX-002 — closed).

## Auth flows

- [ ] `dev-mock-token-*` tokens rejected outside development (test
      `test_dev_bypass_disabled_in_prod.py`).
- [ ] WS handshake requires in-band `{"type":"auth","token":...}` first
      frame (FE-SEC-001) — `?token=` querystring path is NOT used by the
      SPA. Code 4401 on auth failure.
- [ ] Admin WS endpoints (`/ws/stats`, `/ws/test-message`, `/ws/broadcast`)
      return 403 for non-admins (BE-SEC-007).
- [ ] User provisioning is race-safe (BE-CONC-001) — concurrent first-login
      regression test passes.

## Encryption / data at rest

- [ ] No plaintext Plaid tokens in DB (BE-SEC-003) — confirmed by
      `python -m app.services.encryption_migration` reporting zero
      `suspected_plaintext` rows.

## ML worker

- [ ] No legacy `.pkl` prototypes deployed (ML-SEC-001) — only
      `.safetensors`. `ALLOW_LEGACY_PICKLE_LOAD` not set.

## Concurrency / locking

- [ ] Sync lock fence-token Lua CAS-DELETE in place (BE-CONC-002) —
      `backend/tests/concurrency/test_sync_lock_fence.py` green.

## Operator-deferred items

The following findings are **owned by the operator** and require infrastructure
the audit phase intentionally did not provision. They are tracked in
`docs/audit/findings.csv` with status `deferred` rather than `open` —
documented but not blocking the 20-day phase signoff.

| Finding | Action | Why deferred |
|---|---|---|
| INFRA-NGINX-001 | Provision real TLS certs into `nginx/ssl/`; uncomment the 443 server block | needs operator-owned domain + ACME account |
| INFRA-BACKUP-001 | Wire `make backup` cron to a real S3 bucket; set `BACKUP_BUCKET` and lifecycle | needs operator-owned bucket + IAM |
| BE-PR-001 / BE-PR-002 | `alembic revision --autogenerate -m "catchup_baseline"` against a fresh DB; remove `Base.metadata.create_all` from `app/main.py` | needs reachable DB to autogenerate safely |
| ML-PR-005 | `git filter-repo --path ml_models/ --invert-paths` and force-push | history rewrite affects all clones; operator-coordinated |
| FE-PERF-003 | `npm install` in `frontend/` to pick up `react-window`; verify virtualization renders | needs operator's package-lock policy |

## Sign-off

| Check | Reviewer | Date |
|-------|----------|------|
| Above checklist complete |  |  |
| Bandit `bandit -r backend/app` clean |  |  |
| `npm audit --omit=dev` zero high |  |  |
