# 09 — Frontend hygiene + types + ErrorBoundary tree (Day 22)

## Summary

Second day of Phase-2 closeout. Closes four frontend findings. The
type-safety pass (FE-PR-004) is intentionally **left open** — the codebase
has 94+ `any` casts and a credible pass would consume more than this day's
budget; the finding stays in the register so the next phase can pick it up.

## Files edited

| Path:line | Change | Closes |
|---|---|---|
| `frontend/src/App.tsx` (Routes block) | Wrapped each protected route's content in its own `ErrorBoundary` instance so a render error inside one route no longer blank-screens the entire app. Root `ErrorBoundary` retained as the outermost catch. | **FE-PR-002** |
| `frontend/src/hooks/useWebSocket.ts:99-104` | Added an early `return` for `options?.autoConnect === false` at the **top** of the connection effect — before the auth/socket-open path. This prevents the *initial* socket open when the caller passes `autoConnect:false`; the existing teardown effect still handles cleanup of an already-open socket if the flag flips later. | **FE-WS-001** |
| `frontend/src/services/queryClient.ts:113-118` | Added a `dashboard` namespace to the `queryKeys` factory (`all`, `summary()`, `transactionStats()`, `categoryBreakdown()`) so the previously-inline strings `['dashboard']`, `['transactions','stats']`, `['category-breakdown']` route through the factory. | **FE-PR-005** |
| `frontend/src/hooks/usePlaid.ts` | Imports `queryKeys`; replaced the inline `['accounts']`, `['accounts', user?.id]`, `['transactions']`, `['dashboard']`, `['transactions','stats']` literals with `queryKeys.accounts.*`, `queryKeys.transactions.all`, `queryKeys.dashboard.*`. The Plaid-internal `PLAID_KEYS` factory is intentionally kept as a leaf-namespace co-located with the consumer. | **FE-PR-005** |

## Files unchanged but verified

- `frontend/src/utils/envValidation.ts:79` and `frontend/src/hooks/useWebSocket.ts:12` — the two remaining `localhost` references are **env-driven fallbacks** (`import.meta.env.VITE_API_URL || 'http://localhost:8000/api'`, `VITE_WEBSOCKET_URL || 'ws://localhost:8000/ws'`). These are the correct pattern for dev convenience and were the original spirit of FE-PR-003. **Closes FE-PR-003.**

## FE-PR-004 status (kept open, scoped follow-up)

There are 94+ `any` casts across `frontend/src/`. A meaningful pass requires:

1. Audit which `any`s are *legitimate* (third-party type holes, JSON parsing
   boundaries) vs *avoidable* (lazy typing of internal data).
2. Strengthen `frontend/src/types/` with the missing shapes.
3. Replace casts in highest-traffic files first
   (`frontend/src/stores/realtimeStore.ts`, `frontend/src/services/transactionService.ts`).

Estimated effort: ~1 day. Out of the 25-day envelope; tracked in
`docs/audit/findings.csv` row FE-PR-004.

## Verification

- `grep -rn "http://localhost\|ws://localhost" frontend/src/ --include='*.ts' --include='*.tsx'` returns exactly 2 lines, both env-fallbacks.
- `grep -nE "queryKey: \['(accounts|transactions|dashboard)" frontend/src/hooks/usePlaid.ts` returns 0 (was 6).
- `grep -n "ErrorBoundary" frontend/src/App.tsx | wc -l` reports 8+ instances (root + per-route).
- `grep -n "options?.autoConnect === false" frontend/src/hooks/useWebSocket.ts` returns line in the connection effect.

Live (`cd frontend && npm run test:vitest:run && npx tsc --noEmit`) requires
`node_modules`; deferred to operator alongside the rest of the runtime
verifications.

## Open follow-ups

- FE-PR-004 — `any` cast pass. Tracked, not started.
