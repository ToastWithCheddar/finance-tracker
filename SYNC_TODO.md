# Sync Todo List

This document outlines the tasks required to synchronize the frontend with the updated backend API.

## Backend Summary

Here is a list of the current, real endpoints available on the backend:

### Accounts
- `GET /accounts/`: Get all accounts for the current user.
- `POST /accounts/`: Create a new account manually.
- `GET /accounts/{account_id}`: Get a specific account by ID.
- `PUT /accounts/{account_id}`: Update an existing account.
- `DELETE /accounts/{account_id}`: Delete an account.
- `GET /accounts/{account_id}/with-transactions`: Get account with its transactions.
- `POST /accounts/plaid/link-token`: Create Plaid Link token for account connection.
- `POST /accounts/plaid/exchange-token`: Exchange Plaid public token for access token and create accounts.
- `GET /accounts/connection-status`: Get Plaid connection status for user's accounts.
- `POST /accounts/plaid/update-mode`: Update Plaid account to use update mode for authentication.
- `POST /accounts/plaid/disconnect`: Disconnect a Plaid account.
- `POST /accounts/{account_id}/reconcile`: Reconcile account balance with transaction history.
- `POST /accounts/reconcile-all`: Reconcile all user accounts.
- `POST /accounts/{account_id}/reconciliation-entry`: Create manual reconciliation entry to fix balance discrepancy.
- `GET /accounts/{account_id}/reconciliation-history`: Get reconciliation history for an account.
- `GET /accounts/{account_id}/health`: Get comprehensive account health information.
- `POST /accounts/sync-balances`: Manually trigger account balance sync.
- `POST /accounts/sync-transactions`: Sync transactions for specified accounts or all user accounts.
- `GET /accounts/sync-overview`: Get comprehensive sync overview for user's accounts.
- `GET /accounts/{account_id}/sync-status`: Get detailed sync status for a specific account.
- `POST /accounts/sync/schedule-automatic`: Start automatic sync scheduling for user's accounts.
- `GET /accounts/sync/scheduler-status`: Get current scheduler status.
- `POST /accounts/{account_id}/sync/immediate`: Trigger immediate sync for a specific account.
- `PUT /accounts/{account_id}/sync-frequency`: Update sync frequency for an account.

### Analytics
- `GET /analytics/dashboard`: Get aggregated analytics data for the main dashboard.
- `GET /analytics/money-flow`: Get money flow data for Sankey diagram visualization.
- `GET /analytics/spending-heatmap`: Get daily spending data for calendar heatmap visualization.
- `GET /analytics/timeline`: Get financial timeline events.
- `GET /analytics/net-worth-trend`: Get net worth trend data.
- `GET /analytics/cash-flow-waterfall`: Get cash flow waterfall data.
- `GET /analytics/transaction-stats`: Get transaction summary statistics.
- `GET /analytics/transaction-dashboard`: Get comprehensive transaction dashboard analytics.
- `GET /analytics/spending-trends`: Get spending trends over time.

### Auth
- `GET /auth/me`: Get current user.
- `POST /auth/register`: Register a new user.
- `POST /auth/login`: Authenticate a user.
- `POST /auth/logout`: Log out the current user.
- `POST /auth/refresh`: Refresh an access token.
- `POST /auth/request-password-reset`: Send a password reset email.
- `POST /auth/resend-verification`: Resend an email verification link.
- `POST /auth/change-password`: Change the current user's password.
- `GET /auth/health`: Authentication service health check.

### Budgets
- `POST /budgets`: Create a new budget.
- `GET /budgets`: Get budgets with optional filters.
- `GET /budgets/{budget_id}`: Get a budget by ID.
- `PUT /budgets/{budget_id}`: Update a budget.
- `DELETE /budgets/{budget_id}`: Delete a budget.
- `GET /budgets/{budget_id}/progress`: Get detailed budget progress over time.
- `GET /budgets/analytics/summary`: Get budget summary statistics.
- `GET /budgets/analytics/alerts`: Get current budget alerts.
- `GET /budgets/{budget_id}/calendar`: Get budget calendar data for a specific month.

### Categories
- `GET /categories/`: Get all categories.
- `GET /categories/system`: Get all system (default) categories.
- `GET /categories/my`: Get current user's categories.
- `GET /categories/hierarchy`: Get categories organized in hierarchical structure.
- `GET /categories/{category_id}`: Get a specific category by ID.
- `POST /categories/`: Create a new custom category.
- `PUT /categories/{category_id}`: Update a custom category.
- `DELETE /categories/{category_id}`: Delete a custom category.

### Categorization Rules
- `POST /categorization-rules/`: Create a new categorization rule.
- `GET /categorization-rules/`: Get user's categorization rules.
- `GET /categorization-rules/{rule_id}`: Get a specific categorization rule.
- `PUT /categorization-rules/{rule_id}`: Update an existing categorization rule.
- `DELETE /categorization-rules/{rule_id}`: Delete a categorization rule.
- `POST /categorization-rules/{rule_id}/test`: Test rule against historical transactions.
- `POST /categorization-rules/test-conditions`: Test rule conditions against historical transactions.
- `POST /categorization-rules/apply-to-transactions`: Apply categorization rules to specific transactions.
- `GET /categorization-rules/templates`: Get available rule templates.
- `POST /categorization-rules/templates/{template_id}/create-rule`: Create a categorization rule from a template.
- `GET /categorization-rules/statistics`: Get statistics about user's categorization rules.
- `GET /categorization-rules/{rule_id}/effectiveness`: Get effectiveness metrics for a specific rule.
- `POST /categorization-rules/{rule_id}/feedback`: Provide feedback on rule effectiveness.

### Goals
- `POST /goals/`: Create a new financial goal.
- `GET /goals/`: Get user's financial goals.
- `GET /goals/stats`: Get comprehensive goal statistics and analytics.
- `GET /goals/{goal_id}`: Get a specific goal.
- `PUT /goals/{goal_id}`: Update an existing goal.
- `DELETE /goals/{goal_id}`: Delete a goal.
- `POST /goals/{goal_id}/contributions`: Add a contribution to a goal.
- `GET /goals/{goal_id}/contributions`: Get contributions for a specific goal.
- `POST /goals/process-auto-contributions`: Process automatic contributions.
- `GET /goals/types/options`: Get available goal types and priorities.

### Health
- `GET /health`: Health check endpoint.

### Merchants
- `POST /merchants/recognize`: Recognize merchant from transaction description.
- `POST /merchants/transactions/{transaction_id}/enrich`: Enrich a specific transaction with merchant recognition.
- `PUT /merchants/transactions/{transaction_id}/correct`: Correct the merchant for a transaction.
- `GET /merchants/suggestions`: Get merchant suggestions for autocomplete.
- `POST /merchants/bulk-recognize`: Recognize merchants for multiple descriptions at once.
- `GET /merchants/stats`: Get merchant service statistics.
- `DELETE /merchants/cache`: Clear merchant recognition cache.

### ML
- `POST /ml/categorize`: Categorize a single transaction using ML service.
- `POST /ml/feedback`: Submit feedback for ML model improvement.
- `GET /ml/health`: Check ML service health status.
- `GET /ml/stats`: Get ML usage statistics for the current user.
- `POST /ml/batch-categorize`: Categorize multiple transactions in batch.
- `POST /ml/add-example`: Add a new example to a category for improved classification.
- `POST /ml/export-model`: Export the current model to ONNX format.
- `GET /ml/performance`: Get current model performance metrics.

### Notifications
- `GET /notifications/`: Get notifications for the current user.
- `GET /notifications/stats`: Get notification statistics.
- `PATCH /notifications/{notification_id}`: Update a notification.
- `DELETE /notifications/{notification_id}`: Dismiss (delete) a notification.
- `POST /notifications/mark-all-read`: Mark all notifications as read.
- `GET /notifications/{notification_id}`: Get a specific notification by ID.

### Plaid Recurring
- `GET /recurring/plaid/insights`: Get Plaid recurring transaction insights.
- `GET /recurring/plaid/subscriptions`: Get subscription insights from Plaid.
- `POST /recurring/plaid/sync`: Sync latest recurring transaction data from Plaid.
- `GET /recurring/plaid/patterns`: Get recurring transaction patterns detected by Plaid.
- `POST /recurring/plaid/create-rule-from-pattern`: Create a recurring transaction rule from a Plaid-detected pattern.
- `GET /recurring/plaid/spending-trends`: Get trends and analytics for recurring spending from Plaid data.
- `GET /recurring/plaid/upcoming-payments`: Get predicted upcoming recurring payments.

### Saved Filters
- `POST /saved-filters`: Create a new saved filter.
- `GET /saved-filters`: Get all saved filters.
- `GET /saved-filters/{filter_id}`: Get a specific saved filter by ID.
- `PUT /saved-filters/{filter_id}`: Update an existing saved filter.
- `DELETE /saved-filters/{filter_id}`: Delete a saved filter.

### Transactions
- `POST /transactions`: Create a new transaction.
- `GET /transactions/{transaction_id}`: Get a specific transaction.
- `PUT /transactions/{transaction_id}`: Update a transaction.
- `DELETE /transactions/{transaction_id}`: Delete a transaction.
- `GET /transactions`: Get transactions with filters.
- `POST /transactions/import`: Import transactions from a CSV file.
- `POST /transactions/bulk-delete`: Delete multiple transactions at once.
- `GET /transactions/search_transactions`: Advanced search for transactions.
- `GET /transactions/categories`: Get all unique transaction categories.
- `GET /transactions/export`: Export transactions in CSV or JSON format.

### Users
- `GET /users/me`: Get current user's profile.
- `PUT /users/me`: Update current user's profile.
- `DELETE /users/me`: Deactivate current user's account.
- `GET /users/search`: Search users.
- `GET /users/{user_id}`: Get user by ID.
- `GET /users/me/profile`: Get current user's public profile information.
- `GET /users/me/sessions`: Get all active sessions for the current user.
- `GET /users/me/sessions/stats`: Get session statistics for the current user.
- `DELETE /users/me/sessions/{session_id}`: Revoke a specific user session.
- `POST /users/me/sessions/revoke-all`: Revoke all other sessions except the current one.

### Webhooks
- `POST /webhooks/supabase`: Handle incoming Supabase webhook events.
- `POST /webhooks/plaid`: Handle incoming Plaid webhook events.

### WebSockets
- `WS /ws`: Main WebSocket endpoint.
- `GET /ws/health`: Health check for WebSocket service.
- `GET /ws/stats`: Get detailed WebSocket connection statistics.
- `POST /ws/test-message/{user_id}`: Send test message to a user.
- `POST /ws/broadcast`: Broadcast system message to all connected users.

## Task Checklist

### Auth
- [ ] **Task:** Update `LoginForm.tsx` and `RegisterForm.tsx` to use the new `/auth/login` and `/auth/register` endpoints.
  - **Endpoint(s):** `POST /auth/login`, `POST /auth/register`
  - **Changes:**
    - Modify `authStore.ts` to call the new endpoints.
    - Ensure the response format is handled correctly.
  - **Acceptance Criteria:** User can successfully log in and register.

### Accounts
- [ ] **Task:** Update `useAccounts.ts` hook to fetch accounts from `/accounts/`.
  - **Endpoint(s):** `GET /accounts/`
  - **Changes:**
    - Update `accountService.ts` to use the correct endpoint.
    - Ensure the `Account` type in the frontend matches the backend schema.
  - **Acceptance Criteria:** Accounts are displayed correctly on the dashboard.

- [ ] **Task:** Update Plaid integration to use the new endpoints.
  - **Endpoint(s):** `POST /accounts/plaid/link-token`, `POST /accounts/plaid/exchange-token`
  - **Changes:**
    - Update `plaidService.ts` to use the new endpoints.
    - Ensure the frontend handles the new response format.
  - **Acceptance Criteria:** User can successfully connect a bank account via Plaid.

### Transactions
- [ ] **Task:** Update `useTransactions.ts` hook to fetch transactions from `/transactions`.
  - **Endpoint(s):** `GET /transactions`
  - **Changes:**
    - Update `transactionService.ts` to use the correct endpoint and query parameters.
    - Ensure the `Transaction` type in the frontend matches the backend schema.
  - **Acceptance Criteria:** Transactions are displayed correctly in the transactions list.

- [ ] **Task:** Update transaction creation and update forms.
  - **Endpoint(s):** `POST /transactions`, `PUT /transactions/{transaction_id}`
  - **Changes:**
    - Update `TransactionForm.tsx` to use the new endpoints.
    - Ensure the request payloads match the new `TransactionCreate` and `TransactionUpdate` schemas.
  - **Acceptance Criteria:** User can create and update transactions.

- [ ] **Task:** Correct the endpoint for transaction statistics.
  - **Endpoint(s):** `GET /analytics/transaction-stats`
  - **Changes:**
    - In `transactionService.ts`, change the endpoint for `getTransactionStats` from `/analytics/stats` to `/analytics/transaction-stats`.
  - **Acceptance Criteria:** Transaction statistics are fetched and displayed correctly.

- [ ] **Task:** Correct the endpoint for spending trends.
  - **Endpoint(s):** `GET /analytics/spending-trends`
  - **Changes:**
    - In `transactionService.ts`, change the endpoint for `getSpendingTrends` from `/analytics/trends` to `/analytics/spending-trends`.
  - **Acceptance Criteria:** Spending trends are fetched and displayed correctly.

### Budgets
- [ ] **Task:** Update `useBudgets.ts` hook to fetch budgets from `/budgets`.
  - **Endpoint(s):** `GET /budgets`
  - **Changes:**
    - Update `budgetService.ts` to use the correct endpoint.
    - Ensure the `Budget` type in the frontend matches the backend schema.
  - **Acceptance Criteria:** Budgets are displayed correctly on the budgets page.

- [x] **Task:** Update budget analytics to use the new endpoints.
  - **Endpoint(s):** `GET /budgets/analytics/summary`, `GET /budgets/analytics/alerts`, `GET /budgets/{budget_id}/calendar`
  - **Changes:**
    - Update `budgetService.ts` to include methods for the new analytics endpoints.
    - Create or update components to display budget summary, alerts, and calendar views.
  - **Acceptance Criteria:** Budget analytics are displayed correctly on the budget pages.

### Categories
- [ ] **Task:** Update category management to use the new `/categories` endpoints.
  - **Endpoint(s):** `GET /categories`, `POST /categories`, `PUT /categories/{category_id}`, `DELETE /categories/{category_id}`
  - **Changes:**
    - Update `categoryService.ts` to use the new endpoints.
    - Ensure the `Category` type in the frontend matches the backend schema.
  - **Acceptance Criteria:** User can view, create, update, and delete categories.

### Categorization Rules
- [ ] **Task:** Correct the endpoints for import/export.
  - **Endpoint(s):** `GET /categorization-rules/export`, `POST /categorization-rules/import`
  - **Changes:**
    - In `categorizationRulesService.ts`, remove the `/api` prefix from the `exportRules` and `importRules` methods.
  - **Acceptance Criteria:** Users can import and export categorization rules.

- [ ] **Task:** Disable UI for reordering and duplicating rules.
  - **Endpoint(s):** N/A
  - **Changes:**
    - The frontend uses `POST /categorization-rules/reorder` and `POST /categorization-rules/{ruleId}/duplicate`, which are not implemented in the backend.
    - Disable the UI elements that trigger these actions.
    - Add a note to `KNOWN_BROKEN.md` about these features.
  - **Acceptance Criteria:** The UI for reordering and duplicating rules is disabled.

### Plaid Recurring
- [ ] **Task:** Correct the endpoint for exporting recurring transactions.
  - **Endpoint(s):** `GET /recurring/plaid/export`
  - **Changes:**
    - In `plaidRecurringService.ts`, change the endpoint for `exportPlaidRecurringTransactions` to `/recurring/plaid/export`.
  - **Acceptance Criteria:** Users can export Plaid recurring transactions.

### General
- [ ] **Task:** Review all `*Service.ts` files and update any remaining incorrect API calls.
  - **Endpoint(s):** All
  - **Changes:**
    - Systematically go through each service file and verify all API calls against the backend summary.
  - **Acceptance Criteria:** All API calls in the frontend match the available backend endpoints.

- [ ] **Task:** Disable UI components that rely on removed or non-existent endpoints.
  - **Endpoint(s):** N/A
  - **Changes:**
    - Identify any UI components that are making calls to endpoints that no longer exist.
    - Disable or hide these components to prevent errors.
    - Add a note to `KNOWN_BROKEN.md` for each disabled feature.
  - **Acceptance Criteria:** The application runs without errors related to missing API endpoints.
