# Frontend ↔ Backend Sync — TODO

## Rules
- Each task edits ≤ 3 files.
- Don’t invent API fields. Use what the backend currently exposes.
- If backend doesn’t support a thing, disable/guard the UI and (optionally) note it in KNOWN_BROKEN.md.

## Backend summary (Planner fills this)
- Base URL: /api
- Endpoints seen:
  - POST /auth/login → { token, user{id,name} }
  - GET  /auth/me    → { id, name }
  - GET  /transactions?page? → { items[], nextPage? }
  <!-- keep this list short; only what exists -->

## Tasks
- [ ] auth/login — switch to POST /auth/login
  Files: src/store/authStore.ts, src/components/LoginForm.tsx
  Changes:
  - Replace legacy login call with POST /auth/login (email, password)
  - Store {token,user} → keep only fields used elsewhere
  Accept if: typecheck + build pass; login flow works

- [ ] auth/me — current user fetch
  Files: src/store/authStore.ts
  Changes:
  - Replace legacy me-call with GET /auth/me
  - Remove unused fields (e.g., role?) if no longer returned
  Accept if: typecheck + build pass

- [ ] transactions/list
  Files: src/pages/TransactionsPage.tsx, src/services/categoryService.ts
  Changes:
  - Use GET /transactions?page
  - Expect {items,nextPage?}; update pagination
  Accept if: typecheck + build pass; list renders

<!-- Planner adds more tasks similarly -->
