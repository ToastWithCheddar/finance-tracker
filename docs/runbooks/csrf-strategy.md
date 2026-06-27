# CSRF strategy — double-submit cookie

Closes FE-SEC-002.

## Decision

We use the **double-submit cookie** pattern.

- The backend issues a `csrf_token` cookie on every safe-method response
  (`GET`, `HEAD`, `OPTIONS`) when one is not already present.
- The cookie is `Secure` (in non-DEBUG builds), `SameSite=Strict`, and **not**
  `HttpOnly` so the SPA can read it.
- The SPA copies the cookie value into the `X-CSRF-Token` header on every
  mutating request (`POST`, `PUT`, `PATCH`, `DELETE`).
- The middleware compares header against cookie via `secrets.compare_digest`.
  Mismatch or absence -> `403 {"detail":"CSRF token missing or invalid"}`.

## Why not pure SameSite?

`SameSite=Strict` blocks the most common CSRF flows but breaks the SPA
re-auth path on top-level GET navigations from external referrers. Pairing
it with the double-submit header preserves SPA UX while keeping
strict-same-site cookies.

## Implementation pointers

- Backend middleware: `backend/app/main.py` — `csrf_double_submit`.
- Backend toggle: `settings.CSRF_PROTECTION` (default **True**).
- Frontend reader: `frontend/src/services/csrf.ts` (no client-generated
  tokens; pure cookie reader).
- API client header injection: `frontend/src/services/api.ts` — `getHeaders`.

## Exempt paths

- `/ws` — WebSocket handshakes use the in-band auth handshake (FE-SEC-001).
- `/api/auth/login`, `/api/auth/register`, `/api/auth/refresh` — clients
  have no cookie yet on first contact.
- `/api/webhooks/plaid`, `/api/webhooks/supabase` — signed externally.
- `/health`, `/metrics` — must be pingable without auth.

## Rotation

The cookie has no explicit expiry and rotates implicitly:

1. On logout the SPA clears its session — the cookie remains, but is
   useless without a valid `Authorization: Bearer` token.
2. To rotate manually, delete the cookie client-side and trigger a safe
   GET; the middleware re-issues a fresh value.
3. There is no rotation runbook beyond "kill the cookie, hit any GET". The
   cookie carries no identity — it is opaque randomness.

## Verification checklist

- [ ] `curl -i $API/auth/health` returns a `Set-Cookie: csrf_token=...`
- [ ] `curl -X POST $API/transactions -H 'Authorization: Bearer ...'`
      WITHOUT the header returns 403.
- [ ] Same `POST` WITH `X-CSRF-Token` matching the cookie returns 2xx.
