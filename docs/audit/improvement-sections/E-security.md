# Section E — Security

**Owner agent:** Opus 4.7, **high effort** (security debugging requires careful reasoning).

## Scope

Findings: BE-SEC-001..009, BE-CONC-001..002, BE-RL-001, BE-PR-006, FE-SEC-001..002, FE-A11Y-001, ML-SEC-001, INFRA-NGINX-002.

## Tasks (priority order)

### 1. RLS context manager (BE-SEC-001)

In `backend/app/auth/dependencies.py`:
- Convert `get_db_with_user_context` to an async generator dependency:
  ```python
  async def get_db_with_user_context(
      user_id: str = Depends(get_current_user_id),
      db: Session = Depends(get_db),
  ):
      with user_context_db(db, user_id):
          yield db
  ```
- Add positive test: query `current_setting('app.current_user_id', true)` from a route, assert it matches user.
- Add negative test: User A logs in, then attempts to read User B's data via a crafted request; expect empty result (after we add real RLS policies in a follow-up migration).

### 2. Dev-mock-token hardening (BE-SEC-002)

`auth/dependencies.py:74-101`:
- Gate on three flags simultaneously: `settings.ENVIRONMENT == "development" AND settings.DEBUG AND settings.ENABLE_ADMIN_BYPASS`.
- Default `ENABLE_ADMIN_BYPASS=false` in `Settings`.
- Add startup assertion: if any of those is true in non-dev environment, refuse to start.
- Test: with `ENVIRONMENT=production`, assert dev token returns 401.

### 3. Encryption hard-fail (BE-SEC-003)

`encryption_service.py`:
- Remove silent `return plaintext` / `return ciphertext` fallbacks.
- Raise `EncryptionError` (new domain exception); let it bubble to a 500 with structured log.
- Switch key derivation to HKDF: `hkdf.expand(salt=user.id.bytes, info=b"plaid-token", key_material=settings.SECRET_KEY)`.
- Hypothesis property test: for any input string, encrypt then decrypt yields the original.
- Migration consideration: existing rows that were silently corrupted need a one-shot re-encryption script (`docs/runbooks/encryption-migration.md`).

### 4. CSRF replacement (FE-SEC-002)

- Delete `frontend/src/services/csrf.ts`.
- Strategy: rely on `SameSite=Strict` cookies + `Authorization: Bearer` header (auth header alone is sufficient against CSRF if no auth cookie is used). Document in `docs/runbooks/csrf-strategy.md`.
- Or: implement double-submit cookie — server issues `__Host-csrf-token` cookie; client echoes via `X-CSRF-Token`; backend middleware verifies match.

### 5. WS token off the querystring (FE-SEC-001)

- Frontend: open `WebSocket(url)` without token; in `onopen`, send `{ "type": "auth", "token": access_token }`.
- Backend (`routes/websockets.py:24` `WS /ws`): accept connection, then `await ws.receive_json()` first; verify token; if invalid `await ws.close(code=4401)`. Reject all other messages until authenticated.
- Update `useWebSocket.ts` reconnect to repeat the auth handshake.
- Test: connect without sending auth, send a non-auth message, expect 4401 close.

### 6. Rate limiting (BE-RL-001)

- Apply `@limiter.limit("5/minute")` on `/auth/login`, `/auth/request-password-reset`, `/auth/resend-verification`.
- Apply `@limiter.limit("10/hour")` on `/auth/register`.
- Apply `@limiter.limit("60/minute")` on `/api/transactions` and `/api/dashboard/*`.
- Default `RATE_LIMITING=true` in `Settings`.
- Tests under `backend/tests/security/test_rate_limits.py` use a session-scoped Redis container.

### 7. Admin guards (BE-SEC-007)

- Add `is_admin` flag on User model (Alembic migration).
- New dependency `require_admin` returning 403 otherwise.
- Apply to `/ws/stats`, `/ws/test-message/{user_id}`, `/ws/broadcast`.
- Default no admins; doc'd promotion via psql or seed.

### 8. Plaid webhook fix (BE-SEC-006)

- Add `PLAID_BASE_URL` to `Settings` with environment-driven defaults (`https://sandbox.plaid.com`, `https://development.plaid.com`, `https://production.plaid.com`).
- Test: respx-mock Plaid JWKS, send a signed webhook, expect 200; signed-with-wrong-key, expect 401.

### 9. Concurrency (BE-CONC-001..002, BE-PR-006)

- User provisioning: switch to `INSERT ... ON CONFLICT (supabase_user_id) DO NOTHING RETURNING *`, or use `session.merge`.
- Sync lock: include a UUID fence token in the value; release script checks `value == token` before `DEL` (Lua script for atomicity).
- Seed: wrap with Postgres advisory lock `SELECT pg_advisory_xact_lock(...)`.

### 10. Pickle removal (ML-SEC-001)

- `ml_classification_service.py`: replace `pickle.dump/load` of prototypes with `numpy.save/load` of a 2D array + a JSON sidecar mapping category → row index.

### 11. Headers (INFRA-NGINX-002)

In `nginx/nginx.conf`:
- Add `add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; ...";`
- Add `add_header Referrer-Policy "strict-origin-when-cross-origin";`
- Add `add_header Permissions-Policy "geolocation=(), microphone=(), camera=()";`
- Move HSTS exclusively to the 443 server block.

### 12. Frontend a11y (FE-A11Y-001)

- Add `eslint-plugin-jsx-a11y` recommended preset.
- Codemod missing `aria-label`/`role` on spinners, fab buttons, and skeletons.
- Add `Modal` focus trap (verify in `Modal.test.tsx`).

## Deliverables

- New Alembic migration adding `is_admin`, RLS policies (optional, drives further iteration).
- `docs/runbooks/{csrf-strategy,encryption-migration}.md`
- Internship-code edits in `auth/dependencies.py`, `encryption_service.py`, `routes/auth.py`, `routes/websockets.py`, `services/transaction_sync_service.py`, `nginx/nginx.conf`, `frontend/src/hooks/useWebSocket.ts`, `frontend/src/services/csrf.ts` (delete), `frontend/eslint.config.js`.
- Tests under `backend/tests/security/` and `frontend/tests/`.

## Success metrics

- `backend/tests/security/` is green.
- `bandit -r backend/app` produces no high-severity findings.
- `npm audit` produces zero high-severity findings.
- `trivy image` on prod images: zero CRITICAL CVEs.
- Manual pentest checklist (OWASP Top 10) executed and documented in `docs/runbooks/security-checklist.md`.

## Agent prompt template

> Finance-tracker security hardening. Opus 4.7 **high effort** thinking. Read `docs/audit/improvement-sections/E-security.md` and the cross-referenced findings in `findings.csv`. Execute tasks in priority order. Modify internship code at the listed integration points. Every fix needs a corresponding test under `backend/tests/security/` (or frontend). Run `pytest backend/tests/security` after each task. Update findings.csv with status changes.
