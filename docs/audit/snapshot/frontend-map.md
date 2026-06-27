# Frontend snapshot — `frontend/`

React 19.1, TypeScript ~5.8, Vite 7, Tailwind 3.4. Strict tsconfig but ~94 `any` casts across 26 files.

## Stack

- `react` 19.1, `react-dom` 19.1, `react-router-dom` 7.7
- `@tanstack/react-query` 5.83
- `zustand` 5.0.6
- `react-hook-form` 7.61 (no zod/yup — inline RHF rules only)
- `recharts` 3.1, `@nivo/calendar`, `@nivo/sankey`
- `react-plaid-link` 4.1
- **Two toast libs:** `sonner` AND `react-hot-toast` (consolidate to sonner)
- Test: `jest` 29 + `ts-jest` ESM + `@testing-library/react` 16

## Vite config (`vite.config.ts`)

- `envDir: '..'` loads root `.env`.
- HMR port 3001 with `usePolling: true` (Docker on macOS).
- **`build.minify: false`** — production builds ship unminified.
- **`build.sourcemap: true`** — sourcemaps shipped to clients.
- `define: { __DEV__: true }` — always true, leaks into prod.

## Source layout

```
frontend/src/
├── main.tsx
├── App.tsx                     # BrowserRouter, all routes wrapped in ProtectedRoute+Layout
├── index.css
├── setupTests.ts               # mocks ResizeObserver, IntersectionObserver, matchMedia
├── pages/
│   ├── Login.tsx
│   ├── Dashboard.tsx           # 9-line stub (unused; routes use RealtimeDashboard)
│   ├── Transactions.tsx        # 603 LOC
│   ├── Budgets.tsx
│   ├── Categories.tsx          # 527 LOC
│   ├── Goals.tsx
│   ├── Profile.tsx
│   └── __tests__/              # 3 page smoke tests
├── components/
│   ├── auth/                   # LoginForm, RegisterForm
│   ├── common/                 # AuthInitializer, ErrorBoundary (single root), ProtectedRoute
│   ├── ui/                     # Button, Card, CurrencyInput, Modal, Input, MetricCard, ...
│   ├── dashboard/              # RealtimeDashboard (583), NotificationPanel (481), charts
│   ├── transactions/           # CSVImport, TransactionFilters, TransactionForm, TransactionList
│   ├── budgets/, goals/, accounts/, categories/, plaid/, profile/
│   ├── realtime/WebSocketManager.tsx
│   ├── dev-tools/AdminBypassButton.tsx
│   └── layout/                 # Layout, Navigation, CommandPalette, TopBarExtras
├── services/
│   ├── api.ts                  # 504 LOC — fetch wrapper, refresh interceptor
│   ├── base/BaseService.ts     # in-memory cache (overlaps React Query)
│   ├── transactionService.ts   # 704 LOC, snake↔camel normalization
│   ├── accountService.ts, budgetService.ts, goalService.ts, categoryService.ts,
│   ├── notificationService.ts, mlService.ts, userService.ts, dashboardService.ts,
│   ├── plaidService.ts, budgetAlertService.ts, secureStorage.ts, csrf.ts (theatre)
│   ├── queryClient.ts          # query key factory
│   ├── ServiceRegistry.ts, index.ts
├── hooks/                      # useTransactions, useBudgets, useWebSocket, usePlaid, ...
├── stores/
│   ├── authStore.ts            # persisted to localStorage (user + isAuthenticated only)
│   ├── themeStore.ts           # subscribeWithSelector, prefers-color-scheme
│   ├── realtimeStore.ts        # 717 LOC — handleWebSocketMessage central dispatcher
│   └── globalFilters.ts
├── types/                      # api, auth, budgets, category, errors, goals, ml, realtime, transaction, websocket
├── utils/                      # currency, date, envValidation, validation, ...
└── config/navigation.ts
```

## Routing & code splitting

- All routes mounted in `App.tsx:21-127` inside `<ProtectedRoute><Layout>...`.
- Routes: `/login`, `/dashboard`, `/transactions`, `/categories`, `/budgets`, `/goals`, `/profile`.
- **Zero `React.lazy`** — every page (incl. heavy charts via Recharts/Nivo) is in the initial bundle.

## State management

**Zustand stores** — see source layout above.

**TanStack Query** (`services/queryClient.ts`):
- Defaults: `staleTime 5 min`, `gcTime 10 min`, `refetchOnWindowFocus: false`, retry skips 401.
- Global `MutationCache.onError` → forces logout on 401.
- **Key factory** (`queryKeys.transactions/categories/accounts/budgets/goals`) — but Dashboard uses ad-hoc keys (`['dashboard-summary']`, `['category-breakdown', filters]`) and `useTransactions.ts:15-22` defines its own `TRANSACTION_KEYS` parallel to the factory. **Two parallel key systems → invalidation bugs.**

## API client (`services/api.ts`)

- Base URL: `envValidator.getConfig().VITE_API_URL` default `http://localhost:8000/api` (`envValidation.ts:78`).
- Auth header injected from `secureStorage`. **Logs token prefix on every request** (`api.ts:77,79`).
- Built-in token refresh on 401: parses **camelCase** `accessToken`/`refreshToken` (`api.ts:309,314`), but `authStore.login` parses **snake_case** `access_token`/`refresh_token` (`authStore.ts:38-40`). Schema mismatch → silent forced logouts.
- `register` reads `response.accessToken` (`authStore.ts:67`) — likely broken.
- `credentials: 'include'`, plus `X-CSRF-Token` from `csrf.ts` (client-generated; the server cannot validate a token it never issued — security theatre).

## Auth flow

- Tokens in `sessionStorage` (XSS-readable). Cookie fallback for magic link.
- `AuthInitializer` → `checkTokenExpiration` + cache management.
- `ProtectedRoute` redirects to `/login` if `!isAuthenticated`.
- `AdminBypassButton` (dev only, gated by `import.meta.env.PROD`) inserts hardcoded user with token `dev-mock-token-12345`.

## Real-time

`useWebSocket` (`hooks/useWebSocket.ts`, 326 LOC):
- URL: `${VITE_WEBSOCKET_URL || 'ws://localhost:8000/ws'}?token=<accessToken>` — **JWT in querystring → leaks via proxy/access logs**.
- Heartbeat: literal text `'ping'`/`'pong'` every 30s.
- Reconnect: fixed 5-second delay, no exponential backoff, no cap.
- On connect: parallel backfill of last 20 transactions + notifications.
- `realtimeStore.handleWebSocketMessage` dispatches: BALANCE_UPDATE, NEW_TRANSACTION, BUDGET_ALERT, GOAL_*, NOTIFICATION, *_SYNC_COMPLETE, PING.

## Forms

`react-hook-form` only; **no zod/yup**. Inline `register('field', { required, ... })` rules per form. No shared schemas with backend.

`CurrencyInput` stores cents; helpers `parseCurrencyInput`/`formatCurrencyDisplay`. `TransactionForm` keeps **two parallel fields** (`amountCents`/`amount`, `transactionDate`/`transaction_date`, `categoryId`/`category_id`) for backend compatibility — error-prone.

## Existing tests

- `src/__tests__/utils/{mockFactories.ts,testUtils.tsx}`
- `src/pages/__tests__/{Budgets,Dashboard,Transactions}.test.tsx`
- `src/components/budgets/__tests__/BudgetCard.test.tsx`
- `src/components/dashboard/__tests__/RealtimeTransactionFeed.test.tsx`

That's **5 component/page smoke tests**. No service/hook/store tests, no E2E.

## Linting & types

- ESLint: minimal (JS recommended, TS recommended, react-hooks, react-refresh). **No `jsx-a11y`, no `import/order`, no `react/recommended`.**
- TS strict: `noUnusedLocals`, `noUnusedParameters`, `noImplicitAny` — defeated by ~94 `any` casts.
