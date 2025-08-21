# Smoke Checks

Pre-req: Backend running at `http://localhost:8000` and frontend builds.

## Backend Checks
- GET `/health` returns 200 and `{ status: "healthy" | "degraded" }`.
- GET `/api/info` returns 200 (auth-agnostic endpoint for API version information).
- GET `/api/transactions` with valid auth (if enforced) returns 200 and a JSON list or pagination container.

## Frontend Checks
- `npm run build` succeeds.
- Frontend preview check (local development only):
  - Starts `vite preview` server temporarily
  - Verifies the preview server responds with 200
  - Gracefully handles port conflicts or startup failures
  - Automatically skipped in CI environments

## Automation
- Run `./scripts/smoke.sh` for automated checks covering:
  - Backend health and API info endpoints
  - Frontend build verification
  - Optional frontend preview validation (local only)
- Script exits with non-zero code on any failure
- Execution time kept under 2 minutes

