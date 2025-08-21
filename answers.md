# Frontend Integration Answers

This document provides detailed answers to the questions posed in `FRONTEND_SYNC_QUESTIONS.md`, based on an analysis of the `finance-tracker` repository's codebase.

---

## 1) Repo & Runtime

- **Frontend root path:** `frontend/`
- **Package manager:** `npm` (confirmed by `package-lock.json` and `npm ci` commands in `frontend/Dockerfile`)
- **Node/PNPM/Yarn versions:** `node 20.x` (from `FROM node:20-alpine` in `frontend/Dockerfile`)
- **React version:** `19.1.0` (from `frontend/package.json`)
- **Vite version:** `7.0.4` (from `frontend/package.json`)
- **Python version:** `3.11` (from `FROM python:3.11-slim` in `backend/Dockerfile`)
- **Entry points (paths):**
    - **App bootstrap:** `frontend/src/main.tsx`
    - **Router config:** `frontend/src/App.tsx` (uses `react-router-dom`'s `BrowserRouter`, `Routes`, and `Route` components)
    - **Root layout:** `frontend/src/App.tsx` (wraps routes with `Layout` component from `src/components/layout/Layout.tsx`)
- **Providers present:**
    - **TanStack Query:** `QueryClientProvider` is mounted in `frontend/src/App.tsx`, using `queryClient` from `frontend/src/services/queryClient.ts`.
    - **Zustand stores:**
        - `frontend/src/stores/authStore.ts`: Manages authentication state (user, isAuthenticated, loading, error).
        - `frontend/src/stores/globalFilters.ts`: Likely manages global filtering state.
        - `frontend/src/stores/realtimeStore.ts`: Handles WebSocket messages and real-time updates.
        - `frontend/src/stores/themeStore.ts`: Manages UI theme.
    - **Tailwind config present?** `frontend/tailwind.config.cjs`
- **Dev commands (from `frontend/package.json` scripts):**
    ```json
    "dev": "vite --host 0.0.0.0 --port 3000",
    "build": "tsc -b && vite build",
    "build:dev": "tsc -b && vite build --mode development",
    "lint": "eslint .",
    "lint:fix": "eslint . --fix",
    "preview": "vite preview",
    "type-check": "tsc --noEmit",
    "clean": "rm -rf dist node_modules/.vite",
    "test": "jest",
    "test:watch": "jest --watch",
    "test:coverage": "jest --coverage",
    "test:ci": "jest --ci --coverage --watchAll=false"
    ```
- **Current dev errors/warnings:** Cannot be determined from static file analysis.

---

## 2) Environment & Config

- **Frontend env vars in use (names + examples):**
    - `VITE_API_URL`: Default `http://localhost:8000/api`
    - `VITE_WEBSOCKET_URL`: Default `ws://localhost:8000/ws`
    - `VITE_APP_NAME`: Default `Finance Tracker`
    - `VITE_APP_VERSION`: Default `1.0.0`
    - `VITE_ENABLE_DEVTOOLS`: Default `false`
    - `VITE_ADMIN_BYPASS`: Default `false`
    - `VITE_SUPABASE_URL`: (from `.env.example`) e.g., `https://ltkxhcebthobvbqnqzvd.supabase.co`
    - `VITE_SUPABASE_ANON_KEY`: (from `.env.example`) e.g., `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
    - `VITE_PLAID_CLIENT_ID`: (from `.env.example`) e.g., `68930265ee10d40024103644`
    - `VITE_PLAID_SECRET`: (from `.env.example`) e.g., `64f200a56096f66e4baceda0f6c997`
    - `VITE_PLAID_ENV`: (from `.env.example`) e.g., `sandbox`
    - `VITE_FRONTEND_URL`: (from `.env.example`) e.g., `http://localhost:3000`
    - `VITE_USE_MOCK_DATA`: (from `.env.example`) e.g., `false`
    - `VITE_UI_ONLY_MODE`: (from `.env.example`) e.g., `false`
    - `import.meta.env.DEV`, `import.meta.env.PROD`, `import.meta.env.MODE` are used for conditional logic.
- **Backend env vars in use (names + examples - from `backend/app/config.py`):**
    - `DATABASE_URL`: e.g., `postgresql+psycopg2://postgres:devpassword123@localhost:5432/postgres`
    - `SECRET_KEY`: (required for production)
    - `SUPABASE_URL`: e.g., `https://your-project-id.supabase.co`
    - `SUPABASE_ANON_KEY`: e.g., `your-anon-key`
    - `SUPABASE_WEBHOOK_SECRET`: (new)
    - `ENVIRONMENT`: e.g., `development`, `production`
    - `DEBUG`: `true` or `false`
    - `LOG_LEVEL`: e.g., `debug`, `info`, `warning`, `error`
    - `FRONTEND_URL`: e.g., `http://localhost:3000`
    - `ML_SERVICE_URL`: e.g., `http://localhost:8001`
    - `ML_CONFIDENCE_THRESHOLD`: e.g., `0.6`
    - `REDIS_URL`: e.g., `redis://localhost:6379`
    - `ENABLE_ADMIN_BYPASS`: `true` or `false`
    - `CSRF_PROTECTION`: `true` or `false`
    - `RATE_LIMITING`: `true` or `false`
    - `ENABLE_DATABASE`: `true` or `false`
    - `ENABLE_REDIS`: `true` or `false`
    - `ENABLE_ML_WORKER`: `true` or `false`
    - `ENABLE_PLAID`: `true` or `false`
    - `CACHE_DEFAULT_TTL`: e.g., `300` (seconds)
    - `CACHE_DEFAULT_MAX_SIZE`: e.g., `1000`
    - `SYNC_JOBS_CACHE_MAX_SIZE`: e.g., `500`
    - `SYNC_JOBS_CACHE_TTL`: e.g., `900` (seconds)
    - `MERCHANT_CACHE_MAX_SIZE`: e.g., `2000`
    - `MERCHANT_CACHE_TTL`: e.g., `3600` (seconds)
    - `RULE_CACHE_MAX_SIZE`: e.g., `1000`
    - `RULE_CACHE_TTL`: e.g., `300` (seconds)
    - `UVICORN_WORKERS`: e.g., `1`
    - `FINANCIAL_HEALTH_BALANCE_NEGATIVE_PENALTY`: e.g., `30`
    - `FINANCIAL_HEALTH_BALANCE_LOW_BALANCE_THRESHOLD`: e.g., `10000`
    - `FINANCIAL_HEALTH_BALANCE_LOW_BALANCE_PENALTY`: e.g., `20`
    - `FINANCIAL_HEALTH_BALANCE_GOOD_BALANCE_THRESHOLD`: e.g., `100000`
    - `FINANCIAL_HEALTH_BALANCE_GOOD_BALANCE_BONUS`: e.g., `10`
    - `FINANCIAL_HEALTH_ACTIVITY_INACTIVE_PENALTY`: e.g., `20`
    - `FINANCIAL_HEALTH_ACTIVITY_HIGH_ACTIVITY_BONUS`: e.g., `10`
    - `FINANCIAL_HEALTH_ACTIVITY_SYNC_HOURS_THRESHOLD`: e.g., `24`
    - `FINANCIAL_HEALTH_ACTIVITY_SYNC_BONUS`: e.g., `5`
    - `FINANCIAL_HEALTH_CASH_FLOW_POSITIVE_FLOW_BONUS`: e.g., `15`
    - `FINANCIAL_HEALTH_CASH_FLOW_HIGH_SPENDING_THRESHOLD`: e.g., `50000`
    - `FINANCIAL_HEALTH_CASH_FLOW_HIGH_SPENDING_PENALTY`: e.g., `25`
    - `FINANCIAL_HEALTH_DEBT_HIGH_DEBT_RATIO`: e.g., `0.5`
    - `FINANCIAL_HEALTH_DEBT_HIGH_DEBT_PENALTY`: e.g., `30`
    - `FINANCIAL_HEALTH_DEBT_MODERATE_DEBT_RATIO`: e.g., `0.3`
    - `FINANCIAL_HEALTH_DEBT_MODERATE_DEBT_PENALTY`: e.g., `15`
    - `FINANCIAL_HEALTH_INVESTMENT_MIN_INVESTMENT_RATIO`: e.g., `0.1`
    - `FINANCIAL_HEALTH_INVESTMENT_MIN_LIQUID_FOR_INVESTMENT`: e.g., `100000`
    - `FINANCIAL_HEALTH_INVESTMENT_LOW_INVESTMENT_PENALTY`: e.g., `20`
    - `FINANCIAL_HEALTH_INVESTMENT_GOOD_INVESTMENT_RATIO`: e.g., `0.3`
    - `FINANCIAL_HEALTH_INVESTMENT_GOOD_INVESTMENT_BONUS`: e.g., `10`
    - `FINANCIAL_HEALTH_SCORING_BASE_SCORE`: e.g., `100`
    - `FINANCIAL_HEALTH_SCORING_USER_BASE_SCORE`: e.g., `70`
    - `PLAID_PRODUCTS`: e.g., `transactions,accounts,liabilities`
    - `PLAID_COUNTRY_CODES`: e.g., `US`
- **.env files and precedence:** Vite's default precedence: `.env`, `.env.local`, `.env.development`.
- **Timezone/locale/currency defaults:**
    - **Currency:** Primarily `USD` is used as a default (`CurrencyUtils.ts`, `BaseService.ts`). Amounts are handled in `cents` (integer minor units).
    - **Locale:** Primarily `en-US` is used as a default (`CurrencyUtils.ts`, `toLocaleDateString` calls).
    - **Timezone:** `UTC` is mentioned in `AdminBypassButton.tsx` and `main.py` for timestamps. User-configurable timezone is suggested by `profile.timezone` in `ProfileInfo.tsx`.

---

## 3) API Base & OpenAPI

- **Dev API base URL:** `http://localhost:8000/api` (derived from `VITE_API_URL` default and backend router prefixes).
- **OpenAPI JSON path/URL:** `http://localhost:8000/openapi.json` (from `backend/app/main.py`).
- **Any API prefixing:** Yes, most API routes are prefixed with `/api` (e.g., `/api/auth`, `/api/users`, `/api/transactions`).
- **CORS config (backend - from `backend/app/main.py` and `backend/app/config.py`):**
    - `allow_origins`:
        ```
        [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://localhost:3000",
            "https://127.0.0.1:3000",
        ]
        ```
    - `allow_credentials`: `True`
    - `allow_methods`: `["*"]` (all methods)
    - `allow_headers`: `["*"]` (all headers)
    - `expose_headers`: `["X-Process-Time", "X-Request-ID"]`

---

## 4) Auth Model (Supabase/JWT)

- **Frontend auth library:** Custom implementation using `apiClient` (from `frontend/src/services/api.ts`) and `secureStorage` (from `frontend/src/services/secureStorage.ts`). It interacts with the backend's authentication endpoints.
- **Backend accepts which token:**
    - Raw Supabase JWT in `Authorization: Bearer <token>`? **Yes**. The backend (`backend/app/auth/auth_service.py`) uses Supabase's authentication service (`gotrue`) to handle user registration, login, and token refreshing. The `login_user` and `refresh_token` methods return `access_token` and `refresh_token` with `token_type: "bearer"`.
- **Required claims or headers:** The backend relies on standard Supabase JWT claims (e.g., `aud`, `iss`, `sub` (user ID), `exp`, `iat`, `role`). No explicit custom headers like `x-user-id` are required for authentication, as the JWT itself contains the necessary user identification.
- **Session persistence:** The frontend stores `access_token` and `refresh_token` locally using `secureStorage` (which uses `localStorage`). The backend relies on Supabase's session management.
- **Logout and token refresh behavior:**
    - **Logout:** Frontend calls `apiClient.removeAuthTokens()` and `csrfService.clearToken()`. Backend's `logout_user` method calls `self.supabase.client.auth.sign_out()` to invalidate the session on the Supabase side.
    - **Token refresh:** Frontend's `refreshToken` action calls the backend's `/auth/refresh` endpoint with the `refresh_token`. The backend's `refresh_token` method uses `self.supabase.client.auth.refresh_session(refresh_token)` to obtain a new access token from Supabase.

---

## 5) WebSocket (Realtime)

- **WS endpoint:** `ws://localhost:8000/ws` (from `backend/app/routes/websockets.py` and `frontend/src/hooks/useWebSocket.ts`).
- **Auth mechanism:**
    - Query param: `?token=<jwt>` (JWT authentication token passed as a query parameter).
    - Header: Not used for initial connection.
    - Initial auth message payload: Not applicable, authentication is via query param.
    - Subprotocols: None explicitly mentioned.
- **Heartbeats:** The backend (`websockets.py`) has a `handle_ping` function that expects `ping` messages from the client and responds with `pong`. However, the frontend's `useWebSocket.ts` hook does not explicitly send `ping` messages. This is a discrepancy.
- **Reconnection policy:** The frontend (`useWebSocket.ts`) attempts to reconnect after 5 seconds on abnormal WebSocket closure (`event.wasClean` is false). A warning toast is displayed.
- **Core event types to handle now (name + example payload):**
    The `frontend/src/stores/realtimeStore.ts` handles a wide range of event types. The `payload` structure varies per type.
    - `BALANCE_UPDATE`: `{ account_name: string }`
    - `TRANSACTION_CREATED`: `{ id: string, userId: string, accountId: string, categoryId: string, amountCents: number, currency: string, description: string, merchant: string, transactionDate: string, is_income: boolean, category_name?: string, category_emoji?: string, account_name?: string }`
    - `TRANSACTION_UPDATED`: Same as `TRANSACTION_CREATED`
    - `TRANSACTION_DELETED`: `{ id: string }`
    - `BULK_TRANSACTIONS_IMPORTED`: No specific payload shown, triggers toast.
    - `BUDGET_ALERT`: `{ message: string, category?: string, amount?: number }`
    - `GOAL_PROGRESS`: Generic `any` payload, used to update `goalUpdates`.
    - `GOAL_ACHIEVED`: `{ goal_id: string, goal_name: string }`
    - `GOAL_MILESTONE_REACHED`: `{ goal_id: string, goal_name: string, celebration_message: string }`
    - `NOTIFICATION`: `{ notification_type: string, title: string, message: string, priority?: string, action_url?: string }`
    - `WEBHOOK_SYNC_COMPLETE`: `{ success: boolean, total_new_transactions: number }`
    - `TRANSACTION_SYNC_COMPLETE`: `{ new_transactions: number, account_name: string }`
    - `BULK_SYNC_COMPLETE`: `{ total_new_transactions: number, total_errors: number }`
    - `PING`: Handled by frontend, but no pong sent.
    - `PLAID_RECURRING_SYNC`: `{ new_subscriptions: number, updated_subscriptions: number }`
    - `PLAID_RECURRING_UPDATE`: Generic `any` payload.
    - `RECURRING_TRANSACTION_ACTION`: `{ action: string, merchant_name: string }`
    - `CATEGORIZATION_RULE_ACTION`: `{ action: string, rule_name: string, rule_id: string }`
    - `RULE_APPLICATION`: `{ rule_id: string, rule_name: string, transaction_id: string, confidence_score: number }`
    - `RULE_EFFECTIVENESS_UPDATE`: `{ rule_id: string, data: any }`
    - `USER_ACTIVITY`: `{ id: string, type: string, title: string, description: string, timestamp: string, table_name: string, record_id: string, metadata: any }`
- **Message envelope schema (confirm or adjust this template):**
    The frontend expects messages with `type` and `payload`. The backend's `send_to_user` and `broadcast_to_all` methods also use this structure.
    ```json
    {
      "type": "string",
      "payload": { /* event-specific payload */ }
    }
    ```
    The template provided in the question (`id`, `ts`, `actor`, `data`) is not consistently matched by the current implementation. The `timestamp` is often added by the frontend when processing.
- **Dedup/ordering:** No explicit top-level `id` or monotonic `ts` for deduplication or ordering in the message envelope. Transaction IDs are present within the payload for relevant messages.
- **Ack requirements:** Clients send `ping` and receive `pong`. For other messages, there are `_confirmed` responses for `subscribe` and `unsubscribe`. No general `ack` mechanism is explicitly defined.

---

## 6) MVP Endpoints & Types

### Frontend Routes

- `/login`
- `/dashboard`
- `/transactions`
- `/recurring`
- `/categories`
- `/budgets`
- `/goals`
- `/timeline`
- `/settings`
- `/profile`

### Transactions

- **GET list (filters + pagination):**
    - **Path:** `/api/transactions`
    - **Query params (from `backend/app/schemas/transaction.py` `TransactionFilter` and `TransactionPagination`):**
        - `start_date: date | None`
        - `end_date: date | None`
        - `account_id: UUID | None`
        - `category_id: UUID | None`
        - `status: TransactionStatus | None` (enum: "pending", "posted", "cancelled")
        - `min_amount_cents: int | None`
        - `max_amount_cents: int | None`
        - `search_query: str | None` (searches description or merchant)
        - `is_recurring: bool | None`
        - `is_transfer: bool | None`
        - `tags: List[str] | None`
        - `group_by: TransactionGroupBy | None` (enum: "none", "date", "category", "merchant")
        - `limit: int` (default 25, min 1, max 100)
        - `offset: int` (default 0, min 0)
    - **Response shape (`backend/app/schemas/transaction.py` `TransactionListResponse`):**
        ```json
        {
          "transactions": [
            {
              "id": "uuid",
              "account_id": "uuid",
              "amount_cents": 12345,
              "currency": "USD",
              "description": "Coffee Shop",
              "merchant": "Starbucks",
              "transaction_date": "YYYY-MM-DD",
              "category_id": "uuid",
              "status": "posted",
              "is_recurring": false,
              "is_transfer": false,
              "notes": null,
              "tags": [],
              "metadata_json": {},
              "plaid_transaction_id": null,
              "plaid_category": null,
              "authorized_date": null,
              "merchant_logo": null,
              "user_id": "uuid",
              "confidence_score": null,
              "ml_suggested_category_id": null,
              "category_name": "Food & Dining",
              "account_name": "Checking",
              "amount_dollars": 123.45,
              "is_expense": true,
              "is_income": false
            }
          ],
          "total": 100,
          "limit": 25,
          "offset": 0,
          "has_more": true
        }
        ```
- **POST create:**
    - **Path:** `/api/transactions`
    - **Required/optional fields (from `backend/app/schemas/transaction.py` `TransactionCreate`):**
        - `account_id: UUID` (required)
        - `amount_cents: int` (required, or `amount: float` can be provided instead)
        - `currency: CurrencyCode` (optional, default "USD")
        - `description: str` (required)
        - `merchant: str | None` (optional)
        - `transaction_date: date` (required)
        - `category_id: UUID | None` (optional)
        - `status: TransactionStatus` (optional, default "posted")
        - `is_recurring: bool` (optional, default `False`)
        - `is_transfer: bool` (optional, default `False`)
        - `notes: str | None` (optional)
        - `tags: List[str] | None` (optional)
        - `metadata_json: Dict[str, Any] | None` (optional)
        - `plaid_transaction_id: str | None` (optional)
        - `plaid_category: List[str] | None` (optional)
        - `authorized_date: date | None` (optional)
        - `merchant_logo: str | None` (optional)
        - `amount: float | None` (optional, alternative to `amount_cents`)
        - `transaction_type: TransactionType | None` (optional, "income" or "expense", affects `amount_cents` sign)
- **PATCH update:** (Note: Backend uses PUT for update, not PATCH)
    - **Path:** `/api/transactions/{transaction_id}`
    - **Patchable fields (from `backend/app/schemas/transaction.py` `TransactionUpdate`):** All fields are optional.
        - `account_id: UUID | None`
        - `amount_cents: int | None`
        - `currency: str | None`
        - `description: str | None`
        - `merchant: str | None`
        - `transaction_date: date | None`
        - `category_id: UUID | None`
        - `status: TransactionStatus | None`
        - `is_recurring: bool | None`
        - `is_transfer: bool | None`
        - `notes: str | None`
        - `tags: List[str] | None`
- **DELETE remove:**
    - **Path:** `/api/transactions/{transaction_id}`
    - **Soft-delete?** No, it performs a hard delete.
    - **Response shape:** `{"message": "Transaction deleted successfully"}`
- **Response envelope:** For list, it's `TransactionListResponse` with `transactions`, `total`, `limit`, `offset`, `has_more`.

### Accounts

- **GET list:**
    - **Path:** `/api/accounts/`
    - **Response fields (from `backend/app/schemas/account.py` `Account`):**
        ```json
        [
          {
            "id": "uuid",
            "user_id": "uuid",
            "name": "Checking Account",
            "account_type": "checking",
            "balance_cents": 500000,
            "currency": "USD",
            "is_active": true,
            "sync_frequency": "manual",
            "plaid_account_id": null,
            "plaid_item_id": null,
            "last_sync_at": null,
            "account_metadata": null,
            "sync_status": "manual",
            "last_sync_error": null,
            "connection_health": "unknown",
            "created_at": "ISO 8601 datetime",
            "updated_at": "ISO 8601 datetime",
            "balance_dollars": 5000.00,
            "is_plaid_connected": false
          }
        ]
        ```
- **GET summary:**
    - **Path:** `/api/analytics/summary` (This is a general analytics summary, not specific to accounts, but includes account-related aggregates. For account-specific summary, the `AccountListResponse` includes an `AccountSummary` object.)
    - **Response shape (from `backend/app/schemas/account.py` `AccountSummary`):**
        ```json
        {
          "total_accounts": 5,
          "active_accounts": 4,
          "total_balance_cents": 1234567,
          "by_type": {
            "checking": { "count": 2, "balance_cents": 700000 },
            "savings": { "count": 1, "balance_cents": 500000 },
            "credit_card": { "count": 1, "balance_cents": -100000 }
          },
          "plaid_connected": 3,
          "last_sync": "ISO 8601 datetime"
        }
        ```

### Budgets

- **GET summary/progress:**
    - **Summary Path:** `/api/budgets/analytics/summary`
    - **Summary Response Shape (from `backend/app/schemas/budget.py` `BudgetSummary`):**
        ```json
        {
          "total_budgets": 5,
          "active_budgets": 3,
          "total_budgeted_cents": 1000000,
          "total_spent_cents": 750000,
          "total_remaining_cents": 250000,
          "over_budget_count": 1,
          "alert_count": 2
        }
        ```
    - **Progress Path:** `/api/budgets/{budget_id}/progress`
    - **Progress Response Shape (from `backend/app/schemas/budget.py` `BudgetProgress`):**
        ```json
        {
          "budget_id": "uuid",
          "budget_name": "Monthly Food",
          "period_start": "YYYY-MM-DD",
          "period_end": "YYYY-MM-DD",
          "daily_spending": [
            { "date": "YYYY-MM-DD", "amount_cents": 1000 },
            { "date": "YYYY-MM-DD", "amount_cents": 500 }
          ],
          "weekly_spending": [
            { "week": "YYYY-WW", "amount_cents": 7000 }
          ],
          "category_breakdown": [
            { "category": "Groceries", "amount_cents": 50000, "percentage": 0.7 },
            { "category": "Restaurants", "amount_cents": 25000, "percentage": 0.3 }
          ]
        }
        ```
- **CSV Import (Transactions):**
    - **Upload path:** `/api/transactions/import`
    - **Required form field names:** `file` (UploadFile, CSV format)
    - **Async job vs immediate result:** Immediate result.
    - **Response shape:**
        ```json
        {
            "message": "Successfully imported {count} transactions",
            "imported_count": 10,
            "errors": [],
            "transactions": [
                // List of imported TransactionResponse objects
            ]
        }
        ```

---

## 7) Error, Paging, and Conventions

- **Error response schema:**
    - **Standardized fields (from `backend/app/schemas/error.py` `ErrorResponse`):**
        ```json
        {
          "error": true,
          "message": "Human-readable error message",
          "error_code": "MACHINE_READABLE_ERROR_CODE",
          "status_code": 400,
          "timestamp": "2024-01-01T12:00:00Z",
          "path": "/api/resource",
          "request_id": "req_1234567890",
          "details": {}
        }
        ```
    - **Validation Error Example (`ValidationErrorResponse`):**
        ```json
        {
          "error": true,
          "message": "Validation failed",
          "error_code": "VALIDATION_ERROR",
          "status_code": 422,
          "timestamp": "2024-01-01T12:00:00Z",
          "path": "/api/transactions",
          "request_id": "req_1234567890",
          "details": {},
          "validation_errors": [
            {
              "field": "amount",
              "message": "Amount must be greater than 0",
              "code": "VALUE_ERROR"
            }
          ]
        }
        ```
- **Pagination model:** Offset-based pagination is used.
    - **Field names:**
        - For `TransactionListResponse`: `total`, `limit`, `offset`, `has_more`.
        - For `search_transactions` endpoint: `items`, `total`, `page`, `per_page`, `pages`.
- **Date/time format:**
    - Dates (`date` objects): "YYYY-MM-DD" (e.g., `transaction_date`, `start_date`).
    - Datetimes (`datetime` objects): ISO 8601 in UTC (e.g., `created_at`, `updated_at`, `timestamp` in error responses). Example: "2024-01-01T12:00:00Z".
- **Currency handling:**
    - Integer minor units (cents) are consistently used for all amounts (`amount_cents`, `balance_cents`).
    - Frontend converts to/from dollars for display (`amount_dollars` computed field, `CurrencyUtils`).
    - Rounding rules: Not explicitly defined in code, but standard financial rounding (e.g., round half up) is implied for display.

---

## 8) Frontend State & Wiring

- **Existing API wrappers:**
    - `frontend/src/services/api.ts`: Defines `ApiClient` as a singleton `apiClient` (also aliased as `api`). This is the central API wrapper for all HTTP requests (GET, POST, PUT, PATCH, DELETE). It handles authentication, CSRF, URL building, response handling, structured error parsing, and automatic silent token refresh.
- **Query keys (from `frontend/src/services/queryClient.ts` `queryKeys` factory):**
    - Follows a consistent pattern: `[entity, sub_entity, id, filters]`.
    - **Auth:** `['auth', 'user']`
    - **Transactions:** `['transactions']`, `['transactions', 'list']`, `['transactions', 'list', filters]`, `['transactions', 'detail', id]`, `['transactions', 'summary', filters]`
    - **Categories:** `['categories']`, `['categories', 'list']`, `['categories', 'list', filters]`, `['categories', 'detail', id]`
    - **Accounts:** `['accounts']`, `['accounts', 'list']`, `['accounts', 'list', filters]`, `['accounts', 'detail', id]`
    - **Budgets:** `['budgets']`, `['budgets', 'list']`, `['budgets', 'list', filters]`, `['budgets', 'detail']`, `['budgets', 'detail', id]`, `['budgets', 'progress', id]`, `['budgets', 'summary']`, `['budgets', 'alerts']`
    - **Goals:** `['goals']`, `['goals', 'list']`, `['goals', 'list', filters]`, `['goals', 'detail']`, `['goals', 'detail', id]`, `['goals', 'stats']`, `['goals', 'contributions', goalId]`, `['goals', 'options']`
- **Zustand stores in use now:**
    - `frontend/src/stores/authStore.ts`: Authentication state.
    - `frontend/src/stores/globalFilters.ts`: Global filtering state.
    - `frontend/src/stores/realtimeStore.ts`: WebSocket message handling and real-time updates.
    - `frontend/src/stores/themeStore.ts`: UI theme management.
- **Components known to be legacy/problematic:** No explicit mentions found in the codebase.

---

## 9) UI/UX Defaults

- **Design system:** Tailwind CSS is confirmed as the design system. `frontend/tailwind.config.cjs` defines custom colors (including semantic colors like `income`, `expense`, `success`, `warning`, and category-specific colors), custom fonts (`Inter`), background gradients, spacing, and animations. Tailwind tokens are the source of truth.
- **Formatting:**
    - **Date:** Dates are generally formatted using `toLocaleDateString()` with `en-US` locale for display. API communication uses "YYYY-MM-DD" for dates and ISO 8601 in UTC for datetimes.
    - **Money:** Amounts are stored and communicated in integer minor units (cents). The frontend uses `CurrencyUtils` (e.g., `formatCents`, `formatDollars`) to convert to/from dollars and apply currency symbols. The default currency is `USD`.
- **Notifications:**
    - Uses `react-hot-toast` for displaying toasts.
    - **Severity mapping from server priorities:**
        - `toast.success`: Used for success messages (e.g., sync complete, rule applied). Green icon.
        - `toast.error`: Used for error messages (e.g., sync failed, connection error). Red icon.
        - `toast(message, { icon: '⚠️' })`: Used for warnings (e.g., real-time connection lost).
        - `toast(message, { icon: 'ℹ️' })`: Used for info messages (e.g., new subscriptions detected).
    - Position: `bottom-right`.

---

## 10) Dev Experience

- **Sample/test data:**
    - `backend/app/scripts/seed_data.py`: Contains `seed_default_categories()` (creates system categories) and `create_test_user()` (creates "test@example.com" user). These are called during backend application startup.
    - `backend/init.sql`: Contains SQL commands for database initialization.
- **Local login:**
    - A test user with email `test@example.com` is created by `create_test_user()` script. The password is not explicitly set in the script, implying it's handled by Supabase's default registration flow. To log in, a corresponding user must exist in Supabase with a known password.
    - Frontend development URL: `http://localhost:3000`.
- **Lint/format/typecheck commands to use:**
    - **Frontend (from `frontend/package.json`):**
        - `npm run lint`: `eslint .`
        - `npm run lint:fix`: `eslint . --fix`
        - `npm run type-check`: `tsc --noEmit`
        - `npm run test`: `jest`
    - **Backend (from `backend/.pre-commit-config.yaml`):**
        - **Formatting:** `black` (`--line-length=88`), `isort` (`--profile=black`, `--line-length=88`).
        - **Linting:** `flake8` (`--max-line-length=88`, `--extend-ignore=E203,W503`).
        - **Type-checking:** `mypy` (`--ignore-missing-imports`).
- **Any pre-commit hooks we should honor during the changes (from `backend/.pre-commit-config.yaml`):**
    - `pre-commit-hooks`: `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-added-large-files`, `check-json`, `check-toml`, `check-merge-conflict`, `debug-statements`.
    - `black`: Auto-formats Python code.
    - `isort`: Auto-sorts Python imports.
    - `flake8`: Lints Python code.
    - `mypy`: Type-checks Python code.
    - `local` hooks: `import-order-check` (ensures import order), `no-relative-imports` (checks `app/models/`).

---

## 11) Priorities & Scope (Confirm)

- **First-pass, fully working screens (confirmed as in scope):**
    - Auth-guarded dashboard
    - Transactions list + create/update/delete
    - Live updates via WebSocket for transactions
    - Accounts list/summary widget
    - Budget summary widget
- **Anything else mandatory for the first pass (confirmed as in scope):**
    - Basic filters for transactions
    - CSV Import for transactions
    - Goals management (endpoints and schemas exist)
    - Categories management (endpoints and schemas exist)
    - Recurring transactions management (endpoints and schemas exist)
- **Out of scope for now:** No explicit "out of scope" declarations were found in the codebase. The document implies a focus on a "simple, fully-working vertical slice," suggesting that features not directly contributing to this core functionality might be implicitly deferred.

---

## 12) Nice-to-Haves (Optional if quick)

- **Basic saved filters for transactions:** Implemented (backend `saved_filters` router and schema exist).
- **Inline category change with ML confidence tooltip:** Implemented (backend `ml` router and schema exist, `RULE_APPLICATION` event in `realtimeStore.ts` includes `confidence_score`).
- **Retry banner on WS disconnect:** Implemented (`useWebSocket.ts` displays a warning toast on connection loss).
- **Loading skeletons for dashboard widgets:** Cannot confirm from backend code or schemas; requires frontend component inspection.

---

## 13) Attachments

- **OpenAPI JSON path/URL:** `http://localhost:8000/openapi.json`

- **Example payloads for WS event types:**
    - **`TRANSACTION_CREATED`:**
        ```json
        {
          "type": "TRANSACTION_CREATED",
          "payload": {
            "id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
            "userId": "user-uuid-123",
            "accountId": "account-uuid-456",
            "categoryId": "category-uuid-789",
            "amountCents": -2550,
            "currency": "USD",
            "description": "Coffee",
            "merchant": "Local Cafe",
            "transactionDate": "2025-08-20",
            "is_income": false,
            "category_name": "Food & Dining",
            "account_name": "Checking"
          }
        }
        ```
    - **`BALANCE_UPDATE`:**
        ```json
        {
          "type": "BALANCE_UPDATE",
          "payload": {
            "accountId": "account-uuid-456",
            "newBalanceCents": 497450,
            "account_name": "Checking"
          }
        }
        ```
    - **`BUDGET_ALERT`:**
        ```json
        {
          "type": "BUDGET_ALERT",
          "payload": {
            "message": "You are approaching your monthly food budget limit!",
            "category": "Food & Dining",
            "amount": 80000
          }
        }
        ```

- **Sample responses for Transactions list and Accounts summary:**
    - **Transactions list (from `TransactionListResponse`):**
        ```json
        {
          "transactions": [
            {
              "id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
              "account_id": "account-uuid-456",
              "amount_cents": -2550,
              "currency": "USD",
              "description": "Coffee",
              "merchant": "Local Cafe",
              "transaction_date": "2025-08-20",
              "category_id": "category-uuid-789",
              "status": "posted",
              "is_recurring": false,
              "is_transfer": false,
              "notes": null,
              "tags": [],
              "metadata_json": {},
              "plaid_transaction_id": null,
              "plaid_category": null,
              "authorized_date": null,
              "merchant_logo": null,
              "user_id": "user-uuid-123",
              "confidence_score": null,
              "ml_suggested_category_id": null,
              "category_name": "Food & Dining",
              "account_name": "Checking",
              "amount_dollars": -25.50,
              "is_expense": true,
              "is_income": false
            },
            {
              "id": "b2c3d4e5-f6a7-8901-2345-67890abcdef0",
              "account_id": "account-uuid-456",
              "amount_cents": 150000,
              "currency": "USD",
              "description": "Freelance Payment",
              "merchant": null,
              "transaction_date": "2025-08-15",
              "category_id": "category-uuid-abc",
              "status": "posted",
              "is_recurring": false,
              "is_transfer": false,
              "notes": null,
              "tags": [],
              "metadata_json": {},
              "plaid_transaction_id": null,
              "plaid_category": null,
              "authorized_date": null,
              "merchant_logo": null,
              "user_id": "user-uuid-123",
              "confidence_score": null,
              "ml_suggested_category_id": null,
              "category_name": "Income",
              "account_name": "Savings",
              "amount_dollars": 1500.00,
              "is_expense": false,
              "is_income": true
            }
          ],
          "total": 2,
          "limit": 2,
          "offset": 0,
          "has_more": false
        }
        ```
    - **Accounts summary (from `AccountSummary`):**
        ```json
        {
          "total_accounts": 3,
          "active_accounts": 3,
          "total_balance_cents": 600000,
          "by_type": {
            "checking": { "count": 1, "balance_cents": 400000 },
            "savings": { "count": 1, "balance_cents": 200000 },
            "credit_card": { "count": 1, "balance_cents": -50000 }
          },
          "plaid_connected": 2,
          "last_sync": "2025-08-20T10:30:00Z"
        }
        ```
