# finance-tracker E2E (Playwright)

Critical-journey end-to-end suite authored as part of the production-hardening
audit (Wave 4, Section B — Testing). This package is **standalone**: it does
not import from `frontend/` or `backend/` and never modifies internship code.

## Pre-conditions

The suite drives a real running stack. Before running tests:

1. From the repo root, bring the dev stack up:
   ```bash
   docker compose up -d
   ```
   This starts nginx (port 80), backend (FastAPI), frontend (Vite), Postgres,
   Redis, and ml-worker. The default `E2E_BASE_URL` is `http://localhost`
   (the nginx reverse proxy).

2. Wait for `http://localhost/health` and `http://localhost/api/auth/health`
   to return 200.

3. (Optional) Provide Plaid sandbox creds for the `plaid-link` spec:
   ```bash
   export PLAID_SANDBOX_CLIENT_ID=...
   export PLAID_SANDBOX_SECRET=...
   ```
   If absent the spec auto-skips.

## Install

```bash
cd e2e
npm install
npm run install:browsers   # one-time: download Chromium + WebKit binaries
```

## Run

```bash
npm test                    # all projects (chromium-desktop, mobile-safari)
npm run test:headed         # see the browser
npm run test:ui             # interactive Playwright UI
npm run report              # open last HTML report
```

Override the base URL:
```bash
E2E_BASE_URL=https://staging.example.com npm test
```

## Seed-user pattern

Each spec creates its own ephemeral user via the public `POST /api/auth/register`
endpoint with a UUID-suffixed email (`e2e+<uuid>@example.test`) and a fixed
password. This avoids cross-test contamination without requiring a DB reset
hook. See `fixtures/seeded-user.ts` for the helper.

For specs that need an authenticated session, the `LoginPage` page object
performs a real UI login, then subsequent navigations reuse Playwright's
storage state in-memory for that worker.

If your environment requires email confirmation before login, set
`E2E_AUTOCONFIRM=1` to mark the user as confirmed via the dev-only Supabase
admin path (or run with `SUPABASE_AUTH_AUTOCONFIRM=true` on the backend's
GoTrue, which is the dev-compose default).

## Suites

| Spec | Purpose | Gating |
|---|---|---|
| `auth.spec.ts` | register → login → logout | none |
| `plaid-link.spec.ts` | Plaid sandbox link | `test.skip` if `PLAID_SANDBOX_*` unset |
| `transactions.spec.ts` | list, filter, paginate, categorize one | none |
| `budgets.spec.ts` | create budget, see progress | none |
| `dashboard.spec.ts` | summary cards + chart visible | none |
| `websocket-notification.spec.ts` | WS push round-trip | `test.fixme` if `/api/internal/test-notify` 404 (no test hook exists yet — finding **BE-TEST-006**) |
| `accessibility.spec.ts` | axe scan of login + dashboard | baseline for **FE-A11Y-001** |

## Type-check

```bash
npm run typecheck
```

## Notes

- We do **not** ship a `compose.test.yml` here; that is Section B's future
  deliverable. This suite documents the manual `docker compose up -d`
  pre-condition instead.
- All artifacts (test-results/, playwright-report/, node_modules/) are
  git-ignored.
