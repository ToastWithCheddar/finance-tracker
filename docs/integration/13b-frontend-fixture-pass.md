# 13b — Frontend Fixture Pass

Closes the Vitest gap left open at the end of Phase 2. Goal was to take the
suite from 39 passing / 29 failing / 2 skipped up to >= 55 passing without
touching `frontend/src/`.

## Final pass count

```
Test Files  20 passed (20)
     Tests  68 passed | 2 skipped (70)
```

68 / 68 runnable tests pass. The two `.skip` entries are intentional security
pins (FE-SEC-001 WebSocket-token-in-URL, plus one ML threshold case) — they
were skipped before this pass and are not part of the regression budget.

## Root cause

Despite the brief framing the failures as three independent clusters, all 29
failures collapsed into a single underlying defect:

> happy-dom@15.11.7 locks the fetch `Response` body stream after the first
> `Response.json()` / `Response.text()` call. Any code path that reads the
> body more than once — or even reads it once via the message-bridge wrapper
> happy-dom uses internally — throws `TypeError: Invalid state: ReadableStream
> is locked`.

`src/services/api.ts:91` calls `response.json()` exactly once on the success
path, so on paper this should be fine. In practice happy-dom's
`FetchBodyUtility.consumeBodyStream` (node_modules/happy-dom/src/fetch/
utilities/FetchBodyUtility.ts:177) was reliably failing under MSW@2 + Node 22
+ undici. The same handlers work cleanly under jsdom.

This single defect masked itself as the three "clusters" the brief described:
service tests threw catch-block fallbacks ("Failed to create Plaid link
token", etc.), hook tests reported `isSuccess === false` because their
underlying service call rejected, and the auth store leaked the raw
`ERR_INVALID_STATE` because it doesn't wrap its API errors.

## Fix

Switch the global Vitest environment from `happy-dom` to `jsdom`. jsdom is
already installed transitively (via `jest-environment-jsdom` in
`package.json`) and its whatwg-fetch implementation handles single-read body
streams correctly. The environment switch lives in `frontend/vitest.config.ts`
with a comment explaining the why so a future contributor doesn't try to
flip it back.

The only follow-on adjustment was in `tests/hooks/useWebSocket.test.tsx`:
jsdom defines `globalThis.WebSocket` as a non-writable accessor, so the old
direct assignment `globalThis.WebSocket = MockWebSocket` raised
`Cannot assign to read only property 'WebSocket'`. Replaced with
`vi.stubGlobal('WebSocket', MockWebSocket)` plus a matching
`vi.unstubAllGlobals()` in `afterEach`. This works in both happy-dom and
jsdom, so the test is environment-portable if happy-dom is ever revisited.

No MSW handler shape changes were needed — the service-level envelope
handling in `src/services/{plaidService,budgetService,...}.ts` already
accepts both `{success, data: {...}}` and direct shapes, and the existing
handlers in `tests/msw/handlers.ts` were correct. The "envelope mismatch"
hypothesis in the brief turned out to be a red herring: every handler call
was returning the right body, the body just couldn't be read.

## Files modified

- `frontend/vitest.config.ts` — global `environment: 'happy-dom'` -> `'jsdom'`,
  with explanatory comment.
- `frontend/tests/hooks/useWebSocket.test.tsx` — switched WebSocket override
  from a direct global assignment to `vi.stubGlobal` + `vi.unstubAllGlobals`
  in `afterEach`.

## Files NOT modified

- Nothing under `frontend/src/`.
- No MSW handler shapes in `tests/msw/handlers.ts` or anywhere else.
- No service-level test assertions.
- `frontend/package.json` / `package-lock.json`.

## Tests left failing

None. The two remaining `it.skip` entries are intentional and pre-existing:

- `tests/hooks/useWebSocket.test.tsx` — `FE-SEC-001: access token is NOT
  included in the WebSocket URL`. Pinned skip until the implementation moves
  the access token off the query string.
- `tests/services/mlService.test.ts` — one threshold-edge case that depends on
  a fixture flag toggle scheduled for a later pass.

## Re-run command

```bash
cd frontend && npm run test:vitest:run
```

Date: 2026-05-08
