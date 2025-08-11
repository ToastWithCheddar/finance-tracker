# Content from api-reference.md

# API Reference

This document provides a comprehensive reference for the Finance Tracker API. It details all available endpoints, their methods, request/response schemas, and authentication requirements.

## Base URL

`[Your API Base URL]`

## Authentication

All API endpoints require authentication unless otherwise specified. The API uses **Bearer Token** authentication. You must include a valid JWT access token in the `Authorization` header of your requests:

`Authorization: Bearer YOUR_ACCESS_TOKEN`

Access tokens are obtained via the `/auth/login` or `/auth/register` endpoints. Access tokens have a limited lifespan and can be refreshed using the `/auth/refresh` endpoint with a refresh token.

## Error Handling

The API returns standard HTTP status codes to indicate the success or failure of a request. Detailed error information is provided in the response body in JSON format:

```json
{
  "detail": "Error message describing the issue",
  "code": "ERROR_CODE_IDENTIFIER",
  "field": "optional_field_name_if_validation_error",
  "context": {
    "additional_details": "optional_contextual_information"
  }
}
```

Common error codes include:
*   `400 Bad Request`: Invalid request payload or parameters.
*   `401 Unauthorized`: Missing or invalid authentication credentials.
*   `403 Forbidden`: Authenticated user does not have permission to access the resource.
*   `404 Not Found`: The requested resource does not exist.
*   `422 Unprocessable Entity`: Validation error (e.g., invalid data format, missing required fields).
*   `500 Internal Server Error`: An unexpected error occurred on the server.

## Endpoints

### 1. Authentication

**`POST /auth/register`**
*   **Description**: Registers a new user.
*   **Request Body**: `UserRegister` schema
*   **Response**: `AuthResponse` schema
*   **Errors**: `422` (Validation Error), `409` (User already exists)

**`POST /auth/login`**
*   **Description**: Authenticates a user and returns access and refresh tokens.
*   **Request Body**: `UserLogin` schema
*   **Response**: `AuthResponse` schema
*   **Errors**: `401` (Invalid credentials), `422` (Validation Error)

**`POST /auth/refresh`**
*   **Description**: Refreshes an expired access token using a refresh token.
*   **Request Body**: `RefreshTokenRequest` schema
*   **Response**: `AuthResponse` schema
*   **Errors**: `401` (Invalid or expired refresh token)

**`GET /auth/me`**
*   **Description**: Retrieves the profile of the currently authenticated user.
*   **Authentication**: Required
*   **Response**: `User` schema
*   **Errors**: `401` (Unauthorized)

**`POST /auth/forgot-password`**
*   **Description**: Initiates a password reset process.
*   **Request Body**: `{ "email": "user@example.com" }`
*   **Response**: `{ "message": "Password reset email sent." }`
*   **Errors**: `422` (Validation Error)

**`POST /auth/reset-password`**
*   **Description**: Resets user password using a reset token.
*   **Request Body**: `{ "token": "reset_token", "new_password": "new_secure_password" }`
*   **Response**: `{ "message": "Password has been reset successfully." }`
*   **Errors**: `400` (Invalid or expired token), `422` (Validation Error)

**`POST /auth/resend-verification`**
*   **Description**: Resends email verification link.
*   **Request Body**: `{ "email": "user@example.com" }`
*   **Response**: `{ "message": "Verification email sent." }`
*   **Errors**: `422` (Validation Error)

### 2. Users

**`GET /users/me`**
*   **Description**: Retrieves the profile of the currently authenticated user.
*   **Authentication**: Required
*   **Response**: `User` schema
*   **Errors**: `401` (Unauthorized)

**`PUT /users/me`**
*   **Description**: Updates the profile of the currently authenticated user.
*   **Authentication**: Required
*   **Request Body**: `UserUpdate` schema
*   **Response**: `User` schema
*   **Errors**: `401` (Unauthorized), `422` (Validation Error)

**`GET /users/me/preferences`**
*   **Description**: Retrieves the preferences of the currently authenticated user.
*   **Authentication**: Required
*   **Response**: `UserPreferences` schema
*   **Errors**: `401` (Unauthorized)

**`PUT /users/me/preferences`**
*   **Description**: Updates the preferences of the currently authenticated user.
*   **Authentication**: Required
*   **Request Body**: `UserPreferencesUpdate` schema
*   **Response**: `UserPreferences` schema
*   **Errors**: `401` (Unauthorized), `422` (Validation Error)

### 3. Accounts

**`GET /accounts`**
*   **Description**: Retrieves a list of all accounts for the authenticated user.
*   **Authentication**: Required
*   **Query Parameters**:
    *   `is_active` (boolean, optional): Filter by active status.
    *   `account_type` (string, optional): Filter by account type (e.g., `checking`, `savings`).
*   **Response**: `List[Account]` schema
*   **Errors**: `401` (Unauthorized)

**`GET /accounts/{account_id}`**
*   **Description**: Retrieves a specific account by its ID.
*   **Authentication**: Required
*   **Path Parameters**:
    *   `account_id` (UUID): The ID of the account.
*   **Response**: `Account` schema
*   **Errors**: `401` (Unauthorized), `404` (Account not found)

**`POST /accounts`**
*   **Description**: Creates a new account for the authenticated user.
*   **Authentication**: Required
*   **Request Body**: `AccountCreate` schema
*   **Response**: `Account` schema
*   **Errors**: `401` (Unauthorized), `422` (Validation Error)

**`PUT /accounts/{account_id}`**
*   **Description**: Updates an existing account.
*   **Authentication**: Required
*   **Path Parameters**:
    *   `account_id` (UUID): The ID of the account to update.
*   **Request Body**: `AccountUpdate` schema
*   **Response**: `Account` schema
*   **Errors**: `401` (Unauthorized), `404` (Account not found), `422` (Validation Error)

**`DELETE /accounts/{account_id}`**
*   **Description**: Deletes an account.
*   **Authentication**: Required
*   **Path Parameters**:
    *   `account_id` (UUID): The ID of the account to delete.
*   **Response**: `{ "message": "Account deleted successfully." }`
*   **Errors**: `401` (Unauthorized), `404` (Account not found)

#### Plaid Integration

**`POST /accounts/plaid/link-token`**
*   **Description**: Creates a Plaid Link token for initiating the Plaid Link flow.
*   **Authentication**: Required
*   **Response**: `{ "link_token": "string", "expiration": "datetime" }`
*   **Errors**: `401` (Unauthorized)

**`POST /accounts/plaid/exchange-token`**
*   **Description**: Exchanges a Plaid public token for an access token.
*   **Authentication**: Required
*   **Request Body**: `{ "public_token": "string", "metadata": { ... } }`
*   **Response**: `{ "message": "Accounts connected successfully.", "accounts": [Account] }`
*   **Errors**: `400` (Invalid public token), `401` (Unauthorized)

**`GET /accounts/connection-status`**
*   **Description**: Retrieves the connection status of all Plaid-linked accounts.
*   **Authentication**: Required
*   **Response**: `{ "connected": boolean, "accounts": [Account], "message": "string" }`
*   **Errors**: `401` (Unauthorized)

**`POST /accounts/sync-balances`**
*   **Description**: Initiates a manual balance synchronization for Plaid-linked accounts.
*   **Authentication**: Required
*   **Request Body**: `{ "account_ids": ["uuid1", "uuid2"], "force_sync": boolean }` (optional)
*   **Response**: `{ "message": "Balance sync initiated." }`
*   **Errors**: `401` (Unauthorized)

**`POST /accounts/sync-transactions`**
*   **Description**: Initiates a manual transaction synchronization for Plaid-linked accounts.
*   **Authentication**: Required
*   **Request Body**: `{ "account_ids": ["uuid1", "uuid2"], "days": int }` (optional)
*   **Response**: `{ "message": "Transaction sync initiated." }`
*   **Errors**: `401` (Unauthorized)

#### Account Reconciliation

**`POST /accounts/{account_id}/reconcile`**
*   **Description**: Reconciles the balance of a specific account.
*   **Authentication**: Required
*   **Path Parameters**:
    *   `account_id` (UUID): The ID of the account to reconcile.
*   **Response**: `ReconciliationResult` schema
*   **Errors**: `401` (Unauthorized), `404` (Account not found)

**`POST /accounts/{account_id}/reconciliation-entry`**
*   **Description**: Creates a manual reconciliation adjustment entry for an account.
*   **Authentication**: Required
*   **Path Parameters**:
    *   `account_id` (UUID): The ID of the account.
*   **Request Body**: `{ "adjustment_cents": int, "description": "string" }`
*   **Response**: `{ "message": "Reconciliation entry created." }`
*   **Errors**: `401` (Unauthorized), `404` (Account not found), `422` (Validation Error)

### 4. Transactions

**`GET /transactions`**
*   **Description**: Retrieves a list of transactions for the authenticated user, with filtering and pagination.
*   **Authentication**: Required
*   **Query Parameters**:
    *   `account_id` (UUID, optional): Filter by account.
    *   `category_id` (UUID, optional): Filter by category.
    *   `transaction_type` (string, optional): Filter by type (`income`, `expense`).
    *   `start_date` (date, optional): Filter transactions from this date.
    *   `end_date` (date, optional): Filter transactions up to this date.
    *   `min_amount` (float, optional): Filter by minimum amount.
    *   `max_amount` (float, optional): Filter by maximum amount.
    *   `search_query` (string, optional): Search by description or merchant.
    *   `page` (int, optional): Page number (default: 1).
    *   `per_page` (int, optional): Items per page (default: 25).
*   **Response**: `TransactionListResponse` schema
*   **Errors**: `401` (Unauthorized)

**`GET /transactions/{transaction_id}`**
*   **Description**: Retrieves a specific transaction by its ID.
*   **Authentication**: Required
*   **Path Parameters**:
    *   `transaction_id` (UUID): The ID of the transaction.
*   **Response**: `Transaction` schema
*   **Errors**: `401` (Unauthorized), `404` (Transaction not found)

**`POST /transactions`**
*   **Description**: Creates a new transaction.
*   **Authentication**: Required
*   **Request Body**: `TransactionCreate` schema
*   **Response**: `Transaction` schema
*   **Errors**: `401` (Unauthorized), `422` (Validation Error)

**`PUT /transactions/{transaction_id}`**
*   **Description**: Updates an existing transaction.
*   **Authentication**: Required
*   **Path Parameters**:
    *   `transaction_id` (UUID): The ID of the transaction to update.
*   **Request Body**: `TransactionUpdate` schema
*   **Response**: `Transaction` schema
*   **Errors**: `401` (Unauthorized), `404` (Transaction not found), `422` (Validation Error)

**`DELETE /transactions/{transaction_id}`**
*   **Description**: Deletes a transaction.
*   **Authentication**: Required
*   **Path Parameters**:
    *   `transaction_id` (UUID): The ID of the transaction to delete.
*   **Response**: `{ "message": "Transaction deleted successfully." }`
*   **Errors**: `401` (Unauthorized), `404` (Transaction not found)

**`POST /transactions/bulk-delete`**
*   **Description**: Deletes multiple transactions by their IDs.
*   **Authentication**: Required
*   **Request Body**: `{ "transaction_ids": ["uuid1", "uuid2"] }`
*   **Response**: `{ "message": "Transactions deleted successfully.", "deleted_count": int }`
*   **Errors**: `401` (Unauthorized), `422` (Validation Error)

**`POST /transactions/import/csv`**
*   **Description**: Imports transactions from a CSV file.
*   **Authentication**: Required
*   **Request Body**: `multipart/form-data` with a `file` field containing the CSV.
*   **Response**: `CSVImportResponse` schema
*   **Errors**: `401` (Unauthorized), `422` (Invalid CSV format or data)

**`GET /transactions/export`**
*   **Description**: Exports transactions in CSV or JSON format.
*   **Authentication**: Required
*   **Query Parameters**:
    *   `format` (string, required): Export format (`csv` or `json`).
    *   `account_id` (UUID, optional): Filter by account.
    *   `category_id` (UUID, optional): Filter by category.
    *   `transaction_type` (string, optional): Filter by type (`income`, `expense`).
    *   `start_date` (date, optional): Filter transactions from this date.
    *   `end_date` (date, optional): Filter transactions up to this date.
*   **Response**: File download (CSV or JSON)
*   **Errors**: `401` (Unauthorized), `422` (Invalid format)

**`GET /transactions/analytics/stats`**
*   **Description**: Retrieves statistics for transactions (total income, expenses, net amount).
*   **Authentication**: Required
*   **Query Parameters**: (Same as `GET /transactions` for filtering)
*   **Response**: `TransactionStats` schema
*   **Errors**: `401` (Unauthorized)

### 5. Categories

**`GET /categories`**
*   **Description**: Retrieves a list of all categories (system-defined and user-defined).
*   **Authentication**: Required
*   **Query Parameters**:
    *   `include_system` (boolean, optional): Include system categories (default: true).
    *   `parent_only` (boolean, optional): Only return top-level categories.
    *   `search` (string, optional): Search categories by name.
*   **Response**: `List[Category]` schema
*   **Errors**: `401` (Unauthorized)

**`GET /categories/hierarchy`**
*   **Description**: Retrieves categories in a hierarchical structure.
*   **Authentication**: Required
*   **Query Parameters**:
    *   `include_system` (boolean, optional): Include system categories (default: true).
*   **Response**: `List[CategoryWithChildren]` schema
*   **Errors**: `401` (Unauthorized)

**`GET /categories/{category_id}`**
*   **Description**: Retrieves a specific category by its ID.
*   **Authentication**: Required
*   **Path Parameters**:
    *   `category_id` (UUID): The ID of the category.
*   **Response**: `Category` schema
*   **Errors**: `401` (Unauthorized), `404` (Category not found)

**`POST /categories`**
*   **Description**: Creates a new user-defined category.
*   **Authentication**: Required
*   **Request Body**: `CategoryCreate` schema
*   **Response**: `Category` schema
*   **Errors**: `401` (Unauthorized), `422` (Validation Error)

**`PUT /categories/{category_id}`**
*   **Description**: Updates an existing user-defined category.
*   **Authentication**: Required
*   **Path Parameters**:
    *   `category_id` (UUID): The ID of the category to update.
*   **Request Body**: `CategoryUpdate` schema
*   **Response**: `Category` schema
*   **Errors**: `401` (Unauthorized), `403` (Cannot update system category), `404` (Category not found), `422` (Validation Error)

**`DELETE /categories/{category_id}`**
*   **Description**: Deletes a user-defined category.
*   **Authentication**: Required
*   **Path Parameters**:
    *   `category_id` (UUID): The ID of the category to delete.
*   **Response**: `{ "message": "Category deleted successfully." }`
*   **Errors**: `401` (Unauthorized), `403` (Cannot delete system category), `404` (Category not found)

### 6. Budgets

**`GET /budgets`**
*   **Description**: Retrieves a list of budgets for the authenticated user.
*   **Authentication**: Required
*   **Query Parameters**:
    *   `category_id` (UUID, optional): Filter by category.
    *   `period` (string, optional): Filter by budget period (`monthly`, `weekly`, etc.).
    *   `is_active` (boolean, optional): Filter by active status.
    *   `over_budget` (boolean, optional): Filter by budgets that are over budget.
*   **Response**: `BudgetListResponse` schema
*   **Errors**: `401` (Unauthorized)

**`GET /budgets/{budget_id}`**
*   **Description**: Retrieves a specific budget by its ID.
*   **Authentication**: Required
*   **Path Parameters**:
    *   `budget_id` (UUID): The ID of the budget.
*   **Response**: `Budget` schema
*   **Errors**: `401` (Unauthorized), `404` (Budget not found)

**`POST /budgets`**
*   **Description**: Creates a new budget.
*   **Authentication**: Required
*   **Request Body**: `BudgetCreate` schema
*   **Response**: `Budget` schema
*   **Errors**: `401` (Unauthorized), `422` (Validation Error)

**`PUT /budgets/{budget_id}`**
*   **Description**: Updates an existing budget.
*   **Authentication**: Required
*   **Path Parameters**:
    *   `budget_id` (UUID): The ID of the budget to update.
*   **Request Body**: `BudgetUpdate` schema
*   **Response**: `Budget` schema
*   **Errors**: `401` (Unauthorized), `404` (Budget not found), `422` (Validation Error)

**`DELETE /budgets/{budget_id}`**
*   **Description**: Deletes a budget.
*   **Authentication**: Required
*   **Path Parameters**:
    *   `budget_id` (UUID): The ID of the budget to delete.
*   **Response**: `{ "message": "Budget deleted successfully." }`
*   **Errors**: `401` (Unauthorized), `404` (Budget not found)

**`GET /budgets/{budget_id}/progress`**
*   **Description**: Retrieves the progress details for a specific budget.
*   **Authentication**: Required
*   **Path Parameters**:
    *   `budget_id` (UUID): The ID of the budget.
*   **Response**: `BudgetProgress` schema
*   **Errors**: `401` (Unauthorized), `404` (Budget not found)

**`GET /budgets/analytics/summary`**
*   **Description**: Retrieves a summary of budget analytics for the authenticated user.
*   **Authentication**: Required
*   **Response**: `BudgetSummary` schema
*   **Errors**: `401` (Unauthorized)

**`GET /budgets/analytics/alerts`**
*   **Description**: Retrieves a list of active budget alerts for the authenticated user.
*   **Authentication**: Required
*   **Response**: `List[BudgetAlert]` schema
*   **Errors**: `401` (Unauthorized)

### 7. Goals

**`GET /goals`**
*   **Description**: Retrieves a list of financial goals for the authenticated user.
*   **Authentication**: Required
*   **Query Parameters**:
    *   `status` (string, optional): Filter by goal status (`active`, `completed`, `paused`, `cancelled`).
    *   `goal_type` (string, optional): Filter by goal type (`savings`, `debt_payoff`, etc.).
    *   `priority` (string, optional): Filter by priority (`low`, `medium`, `high`, `critical`).
*   **Response**: `GoalsResponse` schema
*   **Errors**: `401` (Unauthorized)

**`GET /goals/{goal_id}`**
*   **Description**: Retrieves a specific goal by its ID.
*   **Authentication**: Required
*   **Path Parameters**:
    *   `goal_id` (UUID): The ID of the goal.
*   **Response**: `Goal` schema
*   **Errors**: `401` (Unauthorized), `404` (Goal not found)

**`POST /goals`**
*   **Description**: Creates a new financial goal.
*   **Authentication**: Required
*   **Request Body**: `GoalCreate` schema
*   **Response**: `Goal` schema
*   **Errors**: `401` (Unauthorized), `422` (Validation Error)

**`PUT /goals/{goal_id}`**
*   **Description**: Updates an existing goal.
*   **Authentication**: Required
*   **Path Parameters**:
    *   `goal_id` (UUID): The ID of the goal to update.
*   **Request Body**: `GoalUpdate` schema
*   **Response**: `Goal` schema
*   **Errors**: `401` (Unauthorized), `404` (Goal not found), `422` (Validation Error)

**`DELETE /goals/{goal_id}`**
*   **Description**: Deletes a goal.
*   **Authentication**: Required
*   **Path Parameters**:
    *   `goal_id` (UUID): The ID of the goal to delete.
*   **Response**: `{ "message": "Goal deleted successfully." }`
*   **Errors**: `401` (Unauthorized), `404` (Goal not found)

**`POST /goals/{goal_id}/contributions`**
*   **Description**: Adds a contribution to a goal.
*   **Authentication**: Required
*   **Path Parameters**:
    *   `goal_id` (UUID): The ID of the goal.
*   **Request Body**: `GoalContributionCreate` schema
*   **Response**: `GoalContribution` schema
*   **Errors**: `401` (Unauthorized), `404` (Goal not found), `422` (Validation Error)

**`GET /goals/{goal_id}/contributions`**
*   **Description**: Retrieves contributions for a specific goal.
*   **Authentication**: Required
*   **Path Parameters**:
    *   `goal_id` (UUID): The ID of the goal.
*   **Response**: `List[GoalContribution]` schema
*   **Errors**: `401` (Unauthorized), `404` (Goal not found)

**`GET /goals/stats`**
*   **Description**: Retrieves overall statistics for financial goals.
*   **Authentication**: Required
*   **Response**: `GoalStats` schema
*   **Errors**: `401` (Unauthorized)

**`POST /goals/process-auto-contributions`**
*   **Description**: Processes automatic contributions for eligible goals.
*   **Authentication**: Required
*   **Response**: `{ "message": "string", "results": { "success": int, "failed": int } }`
*   **Errors**: `401` (Unauthorized)

### 8. Machine Learning (ML)

**`POST /ml/categorise`**
*   **Description**: Categorizes a transaction using the ML model.
*   **Authentication**: Required
*   **Request Body**: `MLCategorizeRequest` schema
*   **Response**: `MLCategorizeResponse` schema
*   **Errors**: `401` (Unauthorized), `422` (Validation Error)

**`POST /ml/batch-categorise`**
*   **Description**: Categorizes multiple transactions in a batch.
*   **Authentication**: Required
*   **Request Body**: `BatchCategorizeRequest` schema
*   **Response**: `List[MLCategorizeResponse]` schema
*   **Errors**: `401` (Unauthorized), `422` (Validation Error)

**`POST /ml/feedback`**
*   **Description**: Submits user feedback to improve the ML model's categorization.
*   **Authentication**: Required
*   **Request Body**: `MLFeedbackRequest` schema
*   **Response**: `{ "message": "Feedback received." }`
*   **Errors**: `401` (Unauthorized), `422` (Validation Error)

**`POST /ml/add-example`**
*   **Description**: Adds a new example to a category for model training.
*   **Authentication**: Required
*   **Request Body**: `CategoryExampleRequest` schema
*   **Response**: `{ "message": "Example added." }`
*   **Errors**: `401` (Unauthorized), `422` (Validation Error)

**`POST /ml/export-model`**
*   **Description**: Exports the current ML model to ONNX format (with quantization).
*   **Authentication**: Required
*   **Response**: `{ "message": "Model exported.", "onnx_path": "string", "quantized_path": "string" }`
*   **Errors**: `401` (Unauthorized), `500` (Export failed)

**`GET /ml/performance`**
*   **Description**: Retrieves performance metrics for the ML model.
*   **Authentication**: Required
*   **Response**: `MLModelPerformance` schema
*   **Errors**: `401` (Unauthorized)

**`GET /ml/health`**
*   **Description**: Retrieves the health status of the ML service.
*   **Authentication**: Required
*   **Response**: `MLHealthStatus` schema
*   **Errors**: `401` (Unauthorized)

### 9. Health Check

**`GET /health`**
*   **Description**: Performs a basic health check of the API.
*   **Authentication**: None
*   **Response**: `{ "status": "ok" }`

**`GET /health/detailed`**
*   **Description**: Performs a detailed health check of the API and its dependencies (database, Redis, Supabase).
*   **Authentication**: None
*   **Response**: `{ "status": "ok", "database": "ok", "redis": "ok", "supabase": "ok" }`

**`GET /health/db`**
*   **Description**: Checks the database connection.
*   **Authentication**: None
*   **Response**: `{ "status": "ok" }`

**`GET /health/auth`**
*   **Description**: Checks the authentication service connection.
*   **Authentication**: None
*   **Response**: `{ "status": "ok" }`

## Schemas

This section provides a reference for the Pydantic schemas used in the API.

### Auth Schemas

**`UserRegister`**
*   `email` (string): User's email address.
*   `password` (string): User's password.
*   `display_name` (string, optional): User's display name.

**`UserLogin`**
*   `email` (string): User's email address.
*   `password` (string): User's password.

**`RefreshTokenRequest`**
*   `refresh_token` (string): The refresh token.

**`AuthResponse`**
*   `user` (`User`): The authenticated user's profile.
*   `access_token` (string): JWT access token.
*   `refresh_token` (string): JWT refresh token.
*   `expires_in` (integer): Access token expiration time in seconds.

### User Schemas

**`User`**
*   `id` (UUID): User ID.
*   `email` (string): User's email.
*   `display_name` (string, optional): User's display name.
*   `avatar_url` (string, optional): URL to user's avatar.
*   `locale` (string): User's locale.
*   `timezone` (string): User's timezone.
*   `currency` (string): User's preferred currency.
*   `created_at` (datetime): Timestamp of user creation.
*   `updated_at` (datetime): Timestamp of last update.
*   `is_active` (boolean): User account active status.

**`UserUpdate`**
*   `email` (string, optional): New email address.
*   `display_name` (string, optional): New display name.
*   `avatar_url` (string, optional): New avatar URL.
*   `locale` (string, optional): New locale.
*   `timezone` (string, optional): New timezone.
*   `currency` (string, optional): New preferred currency.

**`UserPreferences`**
*   `currency` (string): User's preferred currency (e.g., "USD").
*   `date_format` (string): Preferred date format (e.g., "MM/DD/YYYY").
*   `number_format` (string): Preferred number format locale (e.g., "en-US").
*   `theme` (string): UI theme ("light", "dark", "auto").
*   `email_notifications` (boolean): Enable/disable email notifications.
*   `push_notifications` (boolean): Enable/disable push notifications.
*   `transaction_reminders` (boolean): Enable/disable transaction reminders.
*   `budget_alerts` (boolean): Enable/disable budget alerts.
*   `weekly_reports` (boolean): Enable/disable weekly reports.
*   `monthly_reports` (boolean): Enable/disable monthly reports.
*   `data_sharing` (boolean): Enable/disable anonymous data sharing.
*   `analytics_tracking` (boolean): Enable/disable analytics tracking.
*   `default_account_type` (string): Default account type for new transactions.
*   `budget_warning_threshold` (float): Percentage threshold for budget warnings (0.0-1.0).
*   `low_balance_threshold` (float): Balance threshold for low balance alerts.
*   `auto_backup` (boolean): Enable/disable automatic data backup.
*   `backup_frequency` (string): Frequency of automatic backups ("daily", "weekly", "monthly").
*   `startup_page` (string): Default page to load on startup.
*   `items_per_page` (integer): Number of items to display per page in lists.
*   `auto_categorize` (boolean): Enable/disable automatic transaction categorization.

**`UserPreferencesUpdate`**
*   (Partial `UserPreferences` schema)

### Account Schemas

**`AccountCreate`**
*   `name` (string): Account name.
*   `account_type` (string): Type of account (e.g., `checking`, `savings`, `credit_card`).
*   `balance_cents` (integer, optional): Initial balance in cents.
*   `currency` (string, optional): Currency code (default: "USD").

**`AccountUpdate`**
*   (Partial `AccountCreate` schema)

**`Account`**
*   `id` (UUID): Account ID.
*   `user_id` (UUID): Owner user ID.
*   `name` (string): Account name.
*   `account_type` (string): Type of account.
*   `balance_cents` (integer): Current balance in cents.
*   `currency` (string): Currency code.
*   `is_active` (boolean): Active status.
*   `plaid_account_id` (string, optional): Plaid account ID.
*   `plaid_item_id` (string, optional): Plaid item ID.
*   `last_sync_at` (datetime, optional): Last sync timestamp.
*   `sync_status` (string, optional): Sync status (e.g., `synced`, `error`).
*   `connection_health` (string, optional): Connection health (`healthy`, `warning`, `failed`).
*   `created_at` (datetime): Creation timestamp.
*   `updated_at` (datetime): Last update timestamp.

**`ReconciliationResult`**
*   `account_id` (UUID): ID of the reconciled account.
*   `account_name` (string): Name of the account.
*   `recorded_balance` (float): Balance recorded in the system.
*   `calculated_balance` (float): Balance calculated from transactions.
*   `discrepancy` (float): Difference between recorded and calculated balance.
*   `is_reconciled` (boolean): True if reconciled within threshold.
*   `reconciliation_threshold` (float): Threshold for reconciliation.
*   `transaction_count` (integer): Number of transactions considered.
*   `reconciliation_date` (datetime): Date of reconciliation.
*   `suggestions` (List[string]): Suggestions for resolving discrepancies.

### Transaction Schemas

**`TransactionCreate`**
*   `account_id` (UUID): Account ID.
*   `category_id` (UUID, optional): Category ID.
*   `amount_cents` (integer): Amount in cents.
*   `currency` (string, optional): Currency code (default: "USD").
*   `description` (string): Transaction description.
*   `merchant` (string, optional): Merchant name.
*   `transaction_date` (date): Date of transaction.
*   `transaction_type` (string): Type of transaction (`income`, `expense`).
*   `is_recurring` (boolean, optional): Is recurring.
*   `recurring_rule` (object, optional): Recurring rule details.
*   `notes` (string, optional): User notes.
*   `tags` (List[string], optional): Tags.

**`TransactionUpdate`**
*   (Partial `TransactionCreate` schema)

**`Transaction`**
*   `id` (UUID): Transaction ID.
*   `user_id` (UUID): User ID.
*   `account_id` (UUID): Account ID.
*   `category_id` (UUID, optional): Category ID.
*   `amount_cents` (integer): Amount in cents.
*   `currency` (string): Currency code.
*   `description` (string): Description.
*   `merchant` (string, optional): Merchant.
*   `transaction_date` (date): Transaction date.
*   `transaction_type` (string): Type (`income`, `expense`).
*   `is_recurring` (boolean): Is recurring.
*   `created_at` (datetime): Creation timestamp.
*   `updated_at` (datetime): Last update timestamp.

**`TransactionListResponse`**
*   `items` (List[`Transaction`]): List of transactions.
*   `total` (integer): Total number of transactions.
*   `page` (integer): Current page number.
*   `per_page` (integer): Items per page.
*   `pages` (integer): Total number of pages.

**`CSVImportResponse`**
*   `imported_count` (integer): Number of successfully imported transactions.
*   `errors` (List[string]): List of errors encountered during import.
*   `transactions` (List[`Transaction`]): List of imported transactions.

**`TransactionStats`**
*   `total_income` (float): Total income amount.
*   `total_expenses` (float): Total expenses amount.
*   `net_amount` (float): Net amount (income - expenses).
*   `transaction_count` (integer): Total number of transactions.

### Category Schemas

**`CategoryCreate`**
*   `name` (string): Category name.
*   `description` (string, optional): Description.
*   `emoji` (string, optional): Emoji.
*   `color` (string, optional): Hex color code.
*   `parent_id` (UUID, optional): Parent category ID.

**`CategoryUpdate`**
*   (Partial `CategoryCreate` schema)

**`Category`**
*   `id` (UUID): Category ID.
*   `user_id` (UUID, optional): Owner user ID (null for system categories).
*   `name` (string): Name.
*   `description` (string, optional): Description.
*   `emoji` (string, optional): Emoji.
*   `color` (string, optional): Color.
*   `icon` (string, optional): Icon identifier.
*   `parent_id` (UUID, optional): Parent ID.
*   `is_system` (boolean): Is system-defined.
*   `is_active` (boolean): Is active.
*   `sort_order` (integer): Sort order.
*   `created_at` (datetime): Creation timestamp.
*   `updated_at` (datetime): Last update timestamp.

**`CategoryWithChildren`**
*   (Extends `Category` with `children`: List[`CategoryWithChildren`])

### Budget Schemas

**`BudgetCreate`**
*   `name` (string): Budget name.
*   `category_id` (UUID, optional): Category ID.
*   `amount_cents` (integer): Budget amount in cents.
*   `period` (string): Budget period (`monthly`, `weekly`, etc.).
*   `start_date` (date): Start date.
*   `end_date` (date, optional): End date.
*   `alert_threshold` (float, optional): Alert threshold (0.0-1.0).
*   `is_active` (boolean, optional): Is active.

**`BudgetUpdate`**
*   (Partial `BudgetCreate` schema)

**`Budget`**
*   `id` (UUID): Budget ID.
*   `user_id` (UUID): User ID.
*   `category_id` (UUID, optional): Category ID.
*   `category_name` (string, optional): Category name.
*   `name` (string): Name.
*   `amount_cents` (integer): Amount in cents.
*   `period` (string): Period.
*   `start_date` (date): Start date.
*   `end_date` (date, optional): End date.
*   `alert_threshold` (float): Alert threshold.
*   `is_active` (boolean): Is active.
*   `created_at` (datetime): Creation timestamp.
*   `updated_at` (datetime): Last update timestamp.
*   `usage` (`BudgetUsage`, optional): Current usage statistics.

**`BudgetUsage`**
*   `budget_id` (UUID): Budget ID.
*   `spent_cents` (integer): Amount spent in cents.
*   `remaining_cents` (integer): Remaining amount in cents.
*   `percentage_used` (float): Percentage of budget used.
*   `is_over_budget` (boolean): True if over budget.
*   `days_remaining` (integer, optional): Days remaining in period.

**`BudgetListResponse`**
*   `budgets` (List[`Budget`]): List of budgets.
*   `summary` (`BudgetSummary`): Summary statistics.
*   `alerts` (List[`BudgetAlert`]): Active alerts.

**`BudgetSummary`**
*   `total_budgets` (integer): Total number of budgets.
*   `active_budgets` (integer): Number of active budgets.
*   `total_budgeted_cents` (integer): Total budgeted amount.
*   `total_spent_cents` (integer): Total spent amount.
*   `total_remaining_cents` (integer): Total remaining amount.
*   `over_budget_count` (integer): Number of budgets over budget.
*   `alert_count` (integer): Number of active alerts.

**`BudgetProgress`**
*   `budget_id` (UUID): Budget ID.
*   `budget_name` (string): Budget name.
*   `period_start` (date): Period start date.
*   `period_end` (date): Period end date.
*   `daily_spending` (List[object]): Daily spending breakdown.
*   `weekly_spending` (List[object]): Weekly spending breakdown.
*   `category_breakdown` (List[object]): Spending breakdown by category.

**`BudgetAlert`**
*   `budget_id` (UUID): Budget ID.
*   `budget_name` (string): Budget name.
*   `category_name` (string, optional): Category name.
*   `alert_type` (string): Type of alert (`warning`, `exceeded`, `near_end`).
*   `message` (string): Alert message.
*   `percentage_used` (float): Percentage of budget used.
*   `amount_over` (float, optional): Amount over budget.

### Goal Schemas

**`GoalCreate`**
*   `name` (string): Goal name.
*   `description` (string, optional): Description.
*   `target_amount_cents` (integer): Target amount in cents.
*   `goal_type` (string): Type of goal (`savings`, `debt_payoff`, etc.).
*   `priority` (string, optional): Priority (`low`, `medium`, `high`, `critical`).
*   `target_date` (date, optional): Target completion date.
*   `contribution_frequency` (string, optional): Contribution frequency.
*   `monthly_target_cents` (integer, optional): Monthly target amount.
*   `auto_contribute` (boolean, optional): Enable auto-contribution.
*   `auto_contribution_amount_cents` (integer, optional): Auto-contribution amount.
*   `auto_contribution_source` (string, optional): Source account for auto-contribution.
*   `milestone_percentage` (integer, optional): Milestone percentage.

**`GoalUpdate`**
*   (Partial `GoalCreate` schema)

**`Goal`**
*   `id` (UUID): Goal ID.
*   `user_id` (UUID): User ID.
*   `name` (string): Name.
*   `description` (string, optional): Description.
*   `target_amount_cents` (integer): Target amount.
*   `current_amount_cents` (integer): Current amount.
*   `goal_type` (string): Type.
*   `priority` (string): Priority.
*   `status` (string): Status (`active`, `completed`, etc.).
*   `start_date` (date): Start date.
*   `target_date` (date, optional): Target date.
*   `completed_date` (date, optional): Completed date.
*   `last_contribution_date` (date, optional): Last contribution date.
*   `contribution_frequency` (string, optional): Contribution frequency.
*   `monthly_target_cents` (integer, optional): Monthly target.
*   `auto_contribute` (boolean): Auto-contribute enabled.
*   `auto_contribution_amount_cents` (integer, optional): Auto-contribution amount.
*   `auto_contribution_source` (string, optional): Auto-contribution source.
*   `milestone_percentage` (integer): Milestone percentage.
*   `last_milestone_reached` (integer): Last milestone reached.
*   `created_at` (datetime): Creation timestamp.
*   `updated_at` (datetime): Last update timestamp.
*   `progress_percentage` (float): Calculated progress.
*   `remaining_amount_cents` (integer): Remaining amount.
*   `is_completed` (boolean): Is completed.

**`GoalContributionCreate`**
*   `amount_cents` (integer): Contribution amount in cents.
*   `note` (string, optional): Note for the contribution.

**`GoalContribution`**
*   `id` (UUID): Contribution ID.
*   `goal_id` (UUID): Goal ID.
*   `amount_cents` (integer): Amount in cents.
*   `contribution_date` (datetime): Date of contribution.
*   `note` (string, optional): Note.
*   `is_automatic` (boolean): Is automatic.
*   `transaction_id` (UUID, optional): Associated transaction ID.
*   `created_at` (datetime): Creation timestamp.

**`GoalsResponse`**
*   `goals` (List[`Goal`]): List of goals.
*   `total` (integer): Total goals.
*   `active_goals` (integer): Active goals.
*   `completed_goals` (integer): Completed goals.
*   `total_target_amount_cents` (integer): Total target amount.
*   `total_current_amount_cents` (integer): Total current amount.
*   `overall_progress` (float): Overall progress percentage.

**`GoalStats`**
*   `total_goals` (integer): Total goals.
*   `active_goals` (integer): Active goals.
*   `completed_goals` (integer): Completed goals.
*   `paused_goals` (integer): Paused goals.
*   `total_saved_cents` (integer): Total saved.
*   `total_target_cents` (integer): Total target.
*   `average_progress` (float): Average progress.
*   `this_month_contributions_cents` (integer): Contributions this month.
*   `goals_by_type` (object): Goals breakdown by type.
*   `goals_by_priority` (object): Goals breakdown by priority.
*   `contribution_stats` (object): Detailed contribution statistics.

### ML Schemas

**`MLCategorizeRequest`**
*   `description` (string): Transaction description.
*   `amount` (float): Transaction amount.
*   `merchant` (string, optional): Merchant name.

**`MLCategorizeResponse`**
*   `category_id` (string): Predicted category ID.
*   `confidence` (float): Confidence score (0.0-1.0).
*   `confidence_level` (string): Confidence level (`low`, `medium`, `high`).
*   `model_version` (string): Version of the ML model used.
*   `all_similarities` (object, optional): All category similarities.

**`MLFeedbackRequest`**
*   `transaction_id` (UUID): ID of the transaction.
*   `predicted_category` (string): Predicted category name.
*   `actual_category` (string): Actual category name (user-corrected).

**`MLModelPerformance`**
*   `total_predictions` (integer): Total predictions made.
*   `total_feedback` (integer): Total feedback received.
*   `correct_predictions` (integer): Number of correct predictions.
*   `accuracy` (float): Model accuracy.
*   `model_version` (string): Current model version.
*   `categories_count` (integer): Number of categories the model knows.
*   `users_with_feedback` (integer): Number of users who provided feedback.

**`MLHealthStatus`**
*   `status` (string): Health status (`healthy`, `unhealthy`).
*   `model_loaded` (boolean): True if model is loaded.
*   `prototypes_loaded` (boolean): True if prototypes are loaded.
*   `categories_count` (integer): Number of categories.
*   `model_version` (string): Model version.

**`BatchCategorizeRequest`**
*   `transactions` (List[object]): List of transactions to categorize. Each object has `id`, `description`, `amount`, `merchant`.

**`CategoryExampleRequest`**
*   `category` (string): Category name.
*   `example` (string): Example transaction description.


---

# Content from api.md

# **5. API Routes & Endpoints**

### **API Structure Overview**

The FastAPI backend provides a comprehensive REST API with the following route groups:

```
/api/
├── auth/           # Authentication endpoints
├── users/          # User management
├── accounts/       # Account management
├── transactions/   # Transaction CRUD and analytics
├── categories/     # Category management
├── budgets/        # Budget management
├── goals/          # Goal management
├── ml/             # ML service endpoints
├── health/         # Health checks
└── ws/             # WebSocket endpoints
```

#### **Authentication Routes (`/api/auth/`)**

**User Registration & Login:**
```python
POST /api/auth/register
    Request: UserRegister (email, password, first_name, last_name)
    Response: AuthResponse (user, access_token, refresh_token)

POST /api/auth/login
    Request: UserLogin (email, password)
    Response: AuthResponse (user, access_token, refresh_token)

POST /api/auth/logout
    Headers: Authorization: Bearer <token>
    Response: 204 No Content

POST /api/auth/refresh
    Request: RefreshTokenRequest (refresh_token)
    Response: AuthResponse (user, access_token, refresh_token)
```

**Password Management:**
```python
POST /api/auth/request-password-reset
    Request: PasswordResetRequest (email)
    Response: 204 No Content

POST /api/auth/reset-password
    Request: PasswordResetConfirm (token, new_password)
    Response: AuthResponse
```

**Email Verification:**
```python
POST /api/auth/verify-email
    Request: EmailVerification (token, email)
    Response: AuthResponse (success, message)

POST /api/auth/resend-verification
    Request: ResendVerificationRequest (email)
    Response: 204 No Content
```

**Authentication Dependencies:**
- `get_current_user`: Validates JWT token and returns user
- `get_current_active_user`: Ensures user is active
- `require_auth`: Basic authentication requirement

#### **User Routes (`/api/users/`)**

```python
GET /api/users/me
    Response: UserResponse (current user profile)

PUT /api/users/me
    Request: UserUpdate (profile updates)
    Response: UserResponse (updated profile)

DELETE /api/users/me
    Response: {"message": "Account deactivated successfully"}

GET /api/users/search?query={query}&skip={skip}&limit={limit}
    Response: List[UserProfile] (search results)

# User Preferences
GET /api/users/me/preferences
    Response: UserPreferencesResponse

PUT /api/users/me/preferences
    Request: UserPreferencesUpdate
    Response: UserPreferencesResponse
```

#### **Transaction Routes (`/api/transactions/`)**

**Basic CRUD:**
```python
POST /api/transactions/
    Request: TransactionCreate
    Response: TransactionResponse
    Features: Auto-categorization via ML, real-time notifications

GET /api/transactions/{transaction_id}
    Response: TransactionResponse

PUT /api/transactions/{transaction_id}
    Request: TransactionUpdate
    Response: TransactionResponse

DELETE /api/transactions/{transaction_id}
    Response: 204 No Content
```

**Advanced Querying:**
```python
GET /api/transactions/
    Query Parameters:
        - start_date, end_date: Date range filter
        - category: Category filter
        - transaction_type: Type filter
        - min_amount, max_amount: Amount range
        - search_query: Text search
        - page, per_page: Pagination
    Response: PaginatedResponse[TransactionResponse]

GET /api/transactions/search
    Query: Advanced search with multiple filters
    Response: TransactionSearchResponse
```

**Bulk Operations:**
```python
POST /api/transactions/import/csv
    Request: Multipart form with CSV file
    Response: BulkImportResponse (imported_count, errors)

POST /api/transactions/bulk-update
    Request: List[TransactionUpdate]
    Response: List[TransactionResponse]

POST /api/transactions/bulk-categorize
    Request: BulkCategorizeRequest (transaction_ids, category_id)
    Response: BulkOperationResponse
```

**Analytics:**
```python
GET /api/transactions/analytics/spending-by-category
    Query: date_range, category_ids
    Response: SpendingByCategoryResponse

GET /api/transactions/analytics/monthly-trends
    Query: months_back, include_projections
    Response: MonthlyTrendsResponse

GET /api/transactions/analytics/insights
    Response: TransactionInsightsResponse
```

#### **Category Routes (`/api/categories/`)**

```python
GET /api/categories/
    Query: include_system, parent_only, search
    Response: List[CategoryResponse]

POST /api/categories/
    Request: CategoryCreate
    Response: CategoryResponse

PUT /api/categories/{category_id}
    Request: CategoryUpdate
    Response: CategoryResponse

DELETE /api/categories/{category_id}
    Response: 204 No Content

GET /api/categories/hierarchy
    Response: CategoryHierarchyResponse (nested structure)

GET /api/categories/usage-stats
    Response: CategoryUsageStatsResponse
```

#### **Budget Routes (`/api/budgets/`)**

```python
GET /api/budgets/
    Query: category_id, period, is_active, date_range
    Response: List[BudgetResponse]

POST /api/budgets/
    Request: BudgetCreate
    Response: BudgetResponse

PUT /api/budgets/{budget_id}
    Request: BudgetUpdate
    Response: BudgetResponse

DELETE /api/budgets/{budget_id}
    Response: 204 No Content

GET /api/budgets/{budget_id}/usage
    Response: BudgetUsageResponse (spent, remaining, percentage)

GET /api/budgets/summary
    Query: period (current_month, current_year, etc.)
    Response: BudgetSummaryResponse

GET /api/budgets/alerts
    Response: List[BudgetAlert] (over-budget warnings)
```

#### **Goal Routes (`/api/goals/`)**

```python
GET /api/goals/
    Query: status, goal_type, priority
    Response: GoalListResponse (goals, stats)

POST /api/goals/
    Request: GoalCreate
    Response: GoalResponse

GET /api/goals/{goal_id}
    Response: GoalResponse (with contributions and milestones)

PUT /api/goals/{goal_id}
    Request: GoalUpdate
    Response: GoalResponse

DELETE /api/goals/{goal_id}
    Response: 204 No Content

POST /api/goals/{goal_id}/contributions
    Request: GoalContributionCreate
    Response: GoalContributionResponse

GET /api/goals/{goal_id}/contributions
    Response: List[GoalContributionResponse]

GET /api/goals/insights
    Response: GoalInsightsResponse (progress analysis, recommendations)
```

#### **ML Service Routes (`/api/ml/`)**

```python
POST /api/ml/categorize
    Request: MLCategorizeRequest (description, amount, merchant)
    Response: MLCategorizeResponse (predicted_category, confidence)

POST /api/ml/feedback
    Request: MLFeedbackRequest (transaction_id, predicted_category, actual_category)
    Response: MLFeedbackResponse

GET /api/ml/model-performance
    Response: MLModelPerformanceResponse (accuracy, precision, recall)

POST /api/ml/retrain
    Request: MLRetrainRequest (user_id, include_global_data)
    Response: MLRetrainResponse (status, new_accuracy)
```

#### **WebSocket Endpoints (`/ws/`)**

```python
WS /ws/connect
    Authentication: JWT token in query parameter
    Messages:
        - transaction_created: New transaction notification
        - transaction_updated: Transaction update notification
        - budget_alert: Budget threshold exceeded
        - goal_milestone: Goal milestone reached
        - account_sync: Account synchronization status
```

### **API Features**

#### **Authentication & Security**
- JWT-based authentication with refresh tokens
- Supabase integration for user management
- Rate limiting (10 requests/second for API, 5 requests/minute for auth)
- CORS configuration for frontend integration
- Request validation with Pydantic schemas

#### **Error Handling**
- Consistent error response format
- HTTP status code standards
- Detailed error messages for development
- Sanitized error messages for production

#### **Pagination**
- Cursor-based pagination for large datasets
- Configurable page sizes
- Total count information
- Navigation links

#### **Filtering & Search**
- Multi-field filtering capabilities
- Full-text search on descriptions
- Date range filtering
- Amount range filtering
- Category and type filtering

#### **Performance Optimizations**
- Database query optimization with indexes
- Lazy loading for relationships
- Caching for frequently accessed data
- Async/await for I/O operations


---

# Content from architecture.md

# Comprehensive System Architecture Overview

This document provides a high-level overview of the entire finance tracker application's architecture, synthesizing information from the detailed analyses of its backend, frontend, ML worker, and Docker configurations.

## 1. High-Level System Diagram

```mermaid
graph TD
    User[User] -->|Web Browser| Nginx[Nginx Proxy]
    Nginx -->|Static Files| Frontend[Frontend (React)]
    Nginx -->|API Requests| Backend[Backend (FastAPI)]

    Backend -->|Database Operations| PostgreSQL[PostgreSQL DB]
    Backend -->|Caching/Messaging| Redis[Redis]
    Backend -->|Async ML Tasks| MLWorker[ML Worker (Celery)]

    MLWorker -->|Model Storage| MLModels[ML Models]
    MLWorker -->|Database Access| PostgreSQL
    MLWorker -->|Redis Queue| Redis

    subgraph Infrastructure
        PostgreSQL
        Redis
        MLModels
    end

    subgraph Application Services
        Frontend
        Backend
        MLWorker
        Nginx
    end
```

## 2. Core Architectural Principles

*   **Microservices**: The application is composed of several independent, loosely coupled services (Backend API, Frontend UI, ML Worker, Database, Cache) that communicate via well-defined interfaces. This promotes scalability, maintainability, and independent deployment.
*   **Asynchronous Processing**: Heavy or long-running tasks (e.g., ML model training, batch processing) are offloaded to a dedicated ML Worker via a message queue (Redis/Celery), ensuring the main API remains responsive.
*   **Containerization**: Docker and Docker Compose are used to package each service into isolated containers, providing consistent environments across development, testing, and production.
*   **Layered Architecture**: Each service (especially the backend) follows a layered design (e.g., API routes, business logic services, data access layer) to separate concerns.
*   **Real-time Capabilities**: WebSockets enable real-time updates to the frontend, providing an interactive and dynamic user experience.
*   **Observability**: Integrated monitoring (Prometheus) and A/B testing frameworks for ML models allow for continuous performance tracking and data-driven decision-making.

## 3. Service Breakdown

### 3.1. Frontend (React/TypeScript)

*   **Purpose**: Provides the user interface for interacting with the finance tracker application.
*   **Technology Stack**: React, TypeScript, Tailwind CSS, `react-router-dom`.
*   **State Management**:
    *   **React Query**: For server-side state management (data fetching, caching, mutations).
    *   **Zustand**: For global client-side state (authentication, real-time data).
*   **API Communication**: Uses a custom `ApiClient` for all backend interactions, including token management and structured error handling.
*   **Real-time Updates**: Consumes WebSocket messages from the backend for live data updates (e.g., new transactions, budget alerts).
*   **Key Features**: User authentication (login/register), dashboard with analytics, transaction management (CRUD, CSV import/export), budget tracking, category management, goal setting, user preferences.

### 3.2. Backend (FastAPI/Python)

*   **Purpose**: Serves as the core API for the application, handling business logic, data persistence, and communication with external services.
*   **Technology Stack**: FastAPI, Python, SQLAlchemy (ORM), PostgreSQL (database), Redis (cache/message broker).
*   **Authentication**: Manages user authentication and authorization, likely using JWTs.
*   **API Endpoints**: Exposes RESTful API endpoints for accounts, transactions, categories, budgets, goals, user preferences, and analytics.
*   **Business Logic**: Contains the core business rules and orchestrates interactions between different data models and services.
*   **Data Access**: Interacts with PostgreSQL for data storage and retrieval.
*   **Asynchronous Tasks**: Dispatches ML-related tasks to the Celery-based ML Worker via Redis.
*   **WebSockets**: Manages WebSocket connections for real-time data push to the frontend.

### 3.3. ML Worker (Celery/Python)

*   **Purpose**: A dedicated service for performing computationally intensive machine learning tasks asynchronously.
*   **Technology Stack**: Python, Celery (task queue), Redis (message broker), Sentence Transformers, ONNX Runtime.
*   **Core Functionality**:
    *   **Transaction Categorization**: Uses a few-shot learning approach with Sentence Transformers to automatically categorize transactions.
    *   **Model Optimization**: Leverages ONNX for optimized inference and INT8 quantization for performance and reduced model size.
    *   **User Feedback Loop**: Collects user feedback on categorization to continuously improve model accuracy.
    *   **A/B Testing**: Built-in framework for A/B testing different model versions in production.
    *   **Monitoring**: Integrates with Prometheus for real-time performance monitoring and alerting.
*   **Communication**: Receives tasks from the Backend via Redis and sends results back or updates the database directly.

### 3.4. Nginx Proxy

*   **Purpose**: Acts as a reverse proxy and web server, routing incoming requests to the appropriate backend or serving static frontend assets.
*   **Technology Stack**: Nginx.
*   **Key Functions**:
    *   **Static File Serving**: Efficiently serves the compiled React frontend assets.
    *   **API Gateway**: Proxies API requests from the frontend to the Backend service.
    *   **Load Balancing**: Can be configured for load balancing across multiple backend instances (though not explicitly shown in a simple setup).
    *   **SSL Termination**: Handles HTTPS connections, offloading SSL encryption/decryption from the backend services.

## 4. Data Stores

*   **PostgreSQL**:
    *   **Role**: Primary relational database for storing all application data (users, accounts, transactions, categories, budgets, goals, etc.).
    *   **Persistence**: Uses Docker volumes for persistent data storage.
*   **Redis**:
    *   **Role**: In-memory data store used for caching, session management, and as a message broker for Celery (ML Worker).
    *   **Persistence**: Configured with AOF (Append Only File) for data persistence.

## 5. Deployment and Orchestration (Docker Compose)

*   **Containerization**: Each service is containerized using its own `Dockerfile` (Backend, Frontend, ML Worker).
*   **Orchestration**: Docker Compose (`docker-compose.yml` for general use, `docker-compose.dev.yml` for development overrides) defines and links all services.
*   **Development Workflow**: Docker Compose facilitates a streamlined development environment with hot-reloading, volume mounts for code changes, and isolated dependencies.
*   **Production Readiness**: The Docker setup includes considerations for production, such as multi-stage builds for optimized images, non-root users for security, persistent volumes, and Nginx for serving and proxying.
*   **Networking**: A custom Docker network (`finance-network`) ensures seamless communication between services.

## 6. Cross-Cutting Concerns

*   **Security**:
    *   **Authentication/Authorization**: Handled by the Backend API.
    *   **Token Management**: Secure storage of JWTs on the frontend.
    *   **CSRF Protection**: Implemented for API requests.
    *   **Non-root Containers**: Services run as non-root users in Docker containers.
    *   **Environment Variables**: Sensitive configurations are managed via environment variables.
*   **Scalability**: The microservices architecture allows individual services to be scaled independently based on demand. Celery/Redis provide a scalable task queue for ML workloads.
*   **Maintainability**: Clear separation of concerns, modular codebase, and strong typing (TypeScript, Python type hints) contribute to easier maintenance and development.
*   **Observability**: Logging, monitoring (Prometheus), and A/B testing provide insights into system health and performance.

This comprehensive architecture provides a robust, scalable, and maintainable foundation for the finance tracker application, designed to handle complex financial data processing and deliver a rich user experience.

---

# Content from backend.md

# **4. Backend Services & Business Logic**

### **Service Architecture**

The backend's business logic is encapsulated within a well-structured service layer, located in the `backend/app/services` directory. This layer is responsible for interacting with the database, performing business calculations, and integrating with external services like Plaid and the ML worker. The services are designed to be used with FastAPI's dependency injection system, which makes them easy to manage and test.

#### **Core Services**

-   **`base_service.py`**: This file defines a generic `BaseService` class that provides common CRUD (Create, Read, Update, Delete) operations. This base class is inherited by other services to reduce code duplication and enforce a consistent interface for data manipulation.
-   **`user_service.py`**: Handles all business logic related to user management, including creating, retrieving, and updating user profiles.
-   **`transaction_service.py`**: A key service that manages all transaction-related operations. It handles the creation, retrieval, updating, and deletion of transactions, as well as more complex operations like filtering, searching, and importing transactions from CSV files.
-   **`account_service.py`**: Manages the business logic for user accounts.
-   **`category_service.py`**: Handles the logic for both system-defined and user-defined transaction categories, including hierarchical category structures.
-   **`budget_service.py`**: Manages all budget-related business logic, such as creating and updating budgets, calculating budget usage, and generating alerts.
-   **`goal_service.py`**: Encapsulates the business logic for financial goals, including creating, updating, and tracking the progress of goals.

#### **Integration Services**

-   **`plaid_service.py` and `enhanced_plaid_service.py`**: These services are responsible for interacting with the Plaid API. They handle tasks like creating Plaid Link tokens, exchanging public tokens for access tokens, and fetching account and transaction data from Plaid. The `enhanced_plaid_service.py` likely provides a higher-level abstraction over the base `plaid_service.py`.
-   **`transaction_sync_service.py`**: This service is responsible for synchronizing transactions from Plaid into the application's database. It handles duplicate detection and ensures that the transaction data is consistent.
-   **`account_sync_monitor.py`**: This service monitors the status of account synchronization with Plaid, providing insights into the health of the connections.
-   **`automatic_sync_scheduler.py`**: This service manages the scheduling of automatic account synchronization with Plaid, ensuring that the user's data is kept up-to-date.
-   **`ml_client.py`**: This service acts as a client for the machine learning service. It provides a simple interface for categorizing transactions and submitting feedback to the ML model.

#### **Analytics and Insights Services**

-   **`analytics_service.py`**: This service is responsible for generating analytics data for the application, such as the data for the main dashboard.
-   **`account_insights_service.py`**: This service likely provides more advanced analytics and insights about user accounts, such as spending patterns and cash flow analysis.

#### **Utility Services**

-   **`reconciliation_service.py` and `enhanced_reconciliation_service.py`**: These services handle the business logic for reconciling account balances.
-   **`transaction_import_service.py`**: This service is responsible for importing transactions from external sources, such as CSV files.
-   **`user_preferences_service.py`**: This service manages user-specific preferences.
-   **`validation_service.py`**: This service likely provides various validation functions that are used throughout the application.
-   **`monitoring_service.py`**: This service is likely used for monitoring the health and performance of the application.
-   **`mock_data_service.py`**: This service provides mock data for the UI, which is used by the `mock.py` router for frontend development.

---

### **Application Entry Point (`main.py`)**

The `main.py` file is the entry point for the backend FastAPI application. It initializes the FastAPI app, configures middleware, includes routers, and defines exception handlers.

#### **FastAPI App Initialization**

The FastAPI application is initialized with the following parameters:

-   **title**: "Finance Tracker API (Development)"
-   **description**: "A comprehensive personal finance management API with AI-powered insights - DEVELOPMENT MODE"
-   **version**: "1.0.0-dev"
-   **docs_url**: "/docs" (API documentation)
-   **redoc_url**: "/redoc" (Alternative API documentation)
-   **openapi_url**: "/openapi.json" (OpenAPI schema)
-   **lifespan**: A context manager that handles application startup and shutdown events.

#### **Lifespan Events**

The `lifespan` function handles the following events:

-   **Startup**:
    -   Logs application startup information.
    -   Checks the database connection.
    -   Creates the database and tables if they don't exist.
    -   Seeds the database with default categories.
-   **Shutdown**:
    -   Logs application shutdown information.

#### **Middleware**

The application uses the following middleware:

-   **`CORSMiddleware`**: Handles Cross-Origin Resource Sharing (CORS) to allow requests from the frontend.
-   **`SlowAPIMiddleware`**: Implements rate limiting to prevent API abuse. The default limit is set to 1000 requests per minute for development.
-   **Custom Middleware for Process Time**: Adds an `X-Process-Time` header to each response, indicating the time taken to process the request.
-   **Custom Middleware for Request ID**: Adds an `X-Request-ID` header to each response for tracing and logging purposes.
-   **Custom Middleware for Security Headers**: Adds security headers like `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, and `Referrer-Policy` to each response to enhance security.

#### **Exception Handlers**

The application defines custom exception handlers for:

-   **`HTTPException`**: Handles FastAPI's `HTTPException` and logs the error.
-   **`RequestValidationError`**: Handles validation errors for incoming requests and returns a detailed JSON response with the validation errors.
-   **`Exception`**: A general exception handler that catches any unhandled exceptions and returns a JSON response with a 500 status code.

#### **Routers**

The application's API is organized into a collection of routers, with each router handling a specific resource or a logical group of endpoints. This modular approach, a key feature of FastAPI, enhances the organization and maintainability of the codebase. The routers are located in the `backend/app/routes` directory.

##### `accounts.router`

This router manages all aspects of user accounts, with a strong focus on Plaid integration for connecting to financial institutions.

-   **Plaid Integration**: Provides endpoints for creating Plaid Link tokens, exchanging public tokens for access tokens, and syncing account balances.
-   **Account Reconciliation**: Includes endpoints for reconciling account balances with transaction histories and for creating manual reconciliation entries.
-   **Health and Sync Management**: Offers endpoints for checking the health of Plaid connections, managing automatic sync schedules, and getting a detailed overview of account sync status.

##### `analytics.router`

This router is responsible for providing aggregated analytics data for the application.

-   **Dashboard Summary**: Exposes an endpoint to retrieve a summary of analytics data for the main dashboard.

##### `auth.router`

The `auth.router` handles user authentication and authorization. It integrates with Supabase for user management.

-   **Core Authentication**: Provides endpoints for user registration, login, and logout.
-   **Token Management**: Includes an endpoint for refreshing JWT access tokens.
-   **Password and Verification**: Offers endpoints for initiating password resets and resending email verifications.
-   **User Profile**: Contains an endpoint to retrieve the profile of the currently authenticated user.

##### `budget.router`

This router provides a comprehensive set of endpoints for managing budgets.

-   **CRUD Operations**: Allows users to create, read, update, and delete budgets.
-   **Analytics and Progress**: Includes endpoints for tracking budget progress over time and for retrieving budget summary statistics and alerts.

##### `categories.router`

The `categories.router` is responsible for managing transaction categories.

-   **CRUD Operations**: Provides endpoints for creating, reading, updating, and deleting both system-defined and user-defined categories.
-   **Hierarchy**: Offers an endpoint to retrieve the category hierarchy, which is useful for nested category structures in the UI.

##### `goals.router`

This router manages financial goals for users.

-   **CRUD Operations**: Allows users to create, read, update, and delete their financial goals.
-   **Contributions**: Includes endpoints for adding and retrieving contributions to a goal.
-   **Analytics**: Provides endpoints for getting goal statistics and other analytics.

##### `health.router`

The `health.router` provides endpoints to monitor the health of the API and its connected services.

-   **Basic and Detailed Checks**: Offers both a basic health check and a detailed check that verifies the status of the database, Redis, and Supabase.
-   **Service-Specific Checks**: Includes endpoints for checking the health of the database and the authentication service individually.

##### `ml.router` and `mlcategory.router`

These routers handle the integration with the machine learning service for transaction categorization.

-   **`ml.router`**: Provides a high-level interface to the ML service, with endpoints for categorizing transactions and submitting feedback.
-   **`mlcategory.router`**: Seems to be a more direct interface to the ML worker, using Celery for asynchronous task management. It includes endpoints for categorizing transactions, submitting feedback, and managing the ML model itself. There appears to be some overlap between these two routers that might warrant further review.

##### `mock.router`

This router provides a set of mock API endpoints that can be enabled for UI development without a running backend.

-   **Comprehensive Mocking**: Mocks all the major API endpoints, including authentication, accounts, transactions, and more.
-   **Development Utility**: This is a valuable tool for frontend developers, as it allows them to work independently of the backend.

##### `transaction.router`

The `transaction.router` is one of the most extensive routers in the application, handling all aspects of transaction management.

-   **CRUD Operations**: Provides full CRUD functionality for transactions.
-   **Bulk Operations**: Includes endpoints for importing transactions from a CSV file and for bulk-deleting transactions.
-   **Search and Filtering**: Offers advanced search capabilities with multiple filters.
-   **Export**: Allows users to export their transactions in CSV or JSON format.
-   **Analytics**: Provides endpoints for retrieving transaction statistics and trends.

##### `user.router`

This router is responsible for managing user profiles and preferences.

-   **Profile Management**: Allows users to get and update their profile information.
-   **Preferences**: Includes endpoints for managing user-specific preferences.
-   **Search**: Provides an endpoint for searching for users.

##### `websockets.py`

This file defines the WebSocket endpoint for real-time communication with clients.

-   **Real-time Updates**: Handles WebSocket connections for sending real-time updates to clients, such as new transactions or budget alerts.
-   **Authentication and Subscriptions**: Includes logic for authenticating WebSocket connections and for managing subscriptions to different real-time events.

#### **Root Endpoint**

The application has a root endpoint `/` that returns basic information about the API, including its version, environment, and status.

---

# Content from cross-cutting-concerns.md

# Cross-Cutting Concerns

This document addresses system-wide concerns such as security, performance, and error handling, based on the current state of the codebase.

## 1. Security

*   **Authentication:** The backend uses JWTs for authentication. The `python-jose` and `passlib` libraries are used for handling JWTs and hashing passwords.
*   **CORS:** The backend uses `fastapi.middleware.cors.CORSMiddleware` to handle Cross-Origin Resource Sharing.
*   **Rate Limiting:** The `slowapi` library is used to implement rate limiting on the API endpoints.

## 2. Performance

*   **Asynchronous Processing:** The backend uses Celery to run ML tasks asynchronously, which prevents long-running tasks from blocking the main API.
*   **Caching:** Redis is used for caching, which can significantly improve the performance of the application.
*   **Optimized ML Inference:** The use of ONNX suggests that the ML models are optimized for performance.

## 3. Error Handling

*   **Custom Exception Handlers:** The backend has custom exception handlers for `HTTPException`, `RequestValidationError`, and `Exception`. This ensures that errors are handled gracefully and that a standardized error response is returned to the client.
*   **Frontend Error Boundaries:** The frontend uses React error boundaries to prevent the entire application from crashing if a component fails to render.

---

# Content from data-and-schema.md

# **3. Database Schema & Models**

### **Core Models Overview**

The application uses SQLAlchemy ORM with a comprehensive relational schema designed for financial data integrity and performance.

#### **BaseModel (`backend/app/models/base.py`)**
```python
class BaseModel(Base):
    __abstract__ = True

    id: UUID = Primary key (UUID4)
    created_at: DateTime = Server timestamp
    updated_at: DateTime = Auto-updated timestamp
```
All models inherit from BaseModel, providing consistent ID generation and audit timestamps.

#### **User Model (`backend/app/models/user.py`)**
```python
class User(BaseModel):
    __tablename__ = "users"

    # Authentication & Identity
    supabase_user_id: UUID = Unique link to Supabase auth
    email: str = Unique, indexed
    first_name: Optional[str]
    last_name: Optional[str]
    display_name: Optional[str]
    avatar_url: Optional[str]

    # Localization
    locale: str = Default "en-US"
    timezone: str = Default "UTC"
    currency: str = Default "USD"

    # Account Status
    is_active: bool = Default True
    is_verified: bool = Default False

    # Preferences
    notification_email: bool = Default True
    notification_push: bool = Default True
    theme: str = Default "light"
```

**Relationships:**
- One-to-many: accounts, transactions, budgets, goals, insights, categories
- One-to-one: preferences

#### **Account Model (`backend/app/models/account.py`)**
```python
class Account(BaseModel):
    __tablename__ = "accounts"

    user_id: UUID = Foreign key to users
    name: str = Account display name
    account_type: str = checking, savings, credit_card, investment
    balance_cents: BigInteger = Balance in smallest currency unit
    currency: str = Default "USD"
    is_active: bool = Default True

    # Plaid Integration
    plaid_account_id: Optional[str] = Unique Plaid identifier
    plaid_access_token: Optional[str] = Encrypted access token
    plaid_item_id: Optional[str] = Plaid item identifier
    last_sync_at: Optional[DateTime] = Last synchronization timestamp

    # Sync Status & Health
    account_metadata: Optional[JSONB] = Flexible metadata storage
    sync_status: str = manual, syncing, synced, error, disconnected
    last_sync_error: Optional[str] = Error message from last sync
    connection_health: str = healthy, warning, failed, not_connected
    sync_frequency: str = daily, weekly, monthly, manual
```

**Properties:**
- `balance_dollars`: Converts cents to dollars
- `is_plaid_connected`: Checks Plaid connection status
- `needs_sync`: Determines if sync is needed (>24 hours old)

#### **Transaction Model (`backend/app/models/transaction.py`)**
```python
class Transaction(BaseModel):
    __tablename__ = "transactions"

    # Core Transaction Data
    user_id: UUID = Foreign key to users
    account_id: UUID = Foreign key to accounts
    category_id: Optional[UUID] = Foreign key to categories

    # Financial Details
    amount_cents: BigInteger = Amount in smallest currency unit
    currency: str = Default "USD"
    description: str = Transaction description
    merchant: Optional[str] = Merchant name
    merchant_logo: Optional[str] = Merchant logo URL

    # Dates
    transaction_date: Date = Actual transaction date
    authorized_date: Optional[Date] = Authorization date
    posted_date: Optional[Date] = Posted date

    # Status & Classification
    status: str = pending, posted, cancelled
    is_recurring: bool = Subscription/recurring payment flag
    is_transfer: bool = Account transfer flag
    is_hidden: bool = User visibility flag

    # Recurring Transaction Support
    recurring_rule: Optional[JSONB] = Cron-like recurrence rules
    recurring_parent_id: Optional[UUID] = Parent recurring transaction

    # Geographic & Additional Data
    location: Optional[JSONB] = {lat, lng, address, city, state, country}
    notes: Optional[str] = User notes
    tags: Optional[List[str]] = User-defined tags

    # External Integration
    plaid_transaction_id: Optional[str] = Unique Plaid identifier
    plaid_category: Optional[List[str]] = Plaid-provided categories

    # ML/AI Enhancement
    confidence_score: Optional[float] = ML categorization confidence
    ml_suggested_category_id: Optional[UUID] = ML-suggested category
    metadata_json: Optional[JSONB] = Flexible metadata storage
```

**Indexes:**
- `idx_transaction_user_date`: (user_id, transaction_date)
- `idx_transaction_account_date`: (account_id, transaction_date)
- `idx_transaction_category`: (category_id)
- `idx_transaction_merchant`: (merchant)
- `idx_transaction_amount`: (amount_cents)
- `idx_transaction_status`: (status)
- `idx_transaction_plaid_id`: (plaid_transaction_id)
- `idx_transaction_recurring`: (is_recurring)

#### **Category Model (`backend/app/models/category.py`)**
```python
class Category(BaseModel):
    __tablename__ = "categories"

    # Ownership & Identity
    user_id: Optional[UUID] = Foreign key to users (NULL for system categories)
    name: str = Category name
    description: Optional[str] = Category description

    # Visual Representation
    emoji: Optional[str] = Category emoji
    color: Optional[str] = Hex color code
    icon: Optional[str] = Icon identifier

    # Hierarchical Structure
    parent_id: Optional[UUID] = Parent category for subcategories

    # System vs Custom
    is_system: bool = System-defined category flag
    is_active: bool = Active status flag

    # Ordering
    sort_order: int = Display order
```

**Constraints:**
- Unique constraint: (user_id, name)
- Indexes on user_id+name, is_system, parent_id

#### **Budget Model (`backend/app/models/budget.py`)**
```python
class Budget(BaseModel):
    __tablename__ = "budgets"

    user_id: UUID = Foreign key to users
    category_id: Optional[UUID] = Foreign key to categories
    name: str = Budget name
    amount_cents: BigInteger = Budget amount in cents
    period: str = monthly, weekly, yearly
    start_date: Date = Budget start date
    end_date: Optional[Date] = Budget end date
    alert_threshold: float = Alert percentage (default 0.8)
    is_active: bool = Active status
```

#### **Goal Model (`backend/app/models/goal.py`)**
```python
class Goal(BaseModel):
    __tablename__ = "goals"

    # Basic Goal Information
    user_id: UUID = Foreign key to users
    name: str = Goal name
    description: Optional[str] = Goal description
    target_amount_cents: BigInteger = Target amount in cents
    current_amount_cents: BigInteger = Current progress in cents

    # Goal Classification
    goal_type: GoalType = savings, debt_payoff, emergency_fund, investment, purchase, other
    priority: GoalPriority = low, medium, high, critical
    status: GoalStatus = active, completed, paused, cancelled

    # Timeline
    start_date: Optional[Date] = Goal start date
    target_date: Optional[Date] = Target completion date
    completed_date: Optional[Date] = Actual completion date

    # Auto-contribution Settings
    auto_contribute: bool = Automatic contribution flag
    auto_contribution_amount: Optional[BigInteger] = Auto-contribution amount
    auto_contribution_source: Optional[str] = Source account

    # Progress Tracking
    last_contribution_date: Optional[Date] = Last contribution date
    contribution_frequency: ContributionFrequency = daily, weekly, monthly, quarterly, yearly
    monthly_target_cents: Optional[BigInteger] = Monthly target amount
    celebration_message: Optional[str] = Completion message

    # Milestone Configuration
    milestone_percent: int = Milestone percentage (default 25%)
    last_milestone: Optional[int] = Last reached milestone
```

**Properties:**
- `progress_percentage`: Calculated progress percentage
- `remaining`: Remaining amount to reach goal
- `is_achieved`: Goal completion status
- `days_remaining`: Days until target date

#### **Supporting Models**

**GoalContribution** - Individual contributions to goals
**GoalMilestone** - Milestone achievement tracking
**UserPreferences** - User-specific settings and preferences
**Insight** - AI-generated financial insights
**MLModelPerformance** - ML model performance tracking

### **Database Relationships Summary**

```
User (1) ──── (M) Account
User (1) ──── (M) Transaction
User (1) ──── (M) Category
User (1) ──── (M) Budget
User (1) ──── (M) Goal
User (1) ──── (1) UserPreferences

Account (1) ──── (M) Transaction
Category (1) ──── (M) Transaction
Category (1) ──── (M) Budget

Goal (1) ──── (M) GoalContribution
Goal (1) ──── (M) GoalMilestone

Transaction (1) ──── (M) GoalContribution
```

---

### **API Schemas**

The application uses Pydantic models to define the data structures used in the API. These schemas are located in the `backend/app/schemas` directory and are used for data validation, serialization, and documentation.

#### **Common Patterns**

-   **`BaseModel`**: All schemas inherit from Pydantic's `BaseModel`, which provides a solid foundation for creating data models.
-   **`Create`, `Update`, and Response Models**: For each resource, there are typically three types of schemas:
    -   A `Create` schema (e.g., `TransactionCreate`) for creating new resources. These schemas typically exclude fields that are generated by the server, such as `id` and `created_at`.
    -   An `Update` schema (e.g., `TransactionUpdate`) for updating existing resources. These schemas typically have all fields marked as optional, allowing for partial updates.
    -   A response schema (e.g., `Transaction`) for returning data from the API. These schemas represent the full data model, including all server-generated fields.
-   **Data Validation**: Pydantic's validation features are used to enforce data types and constraints, which helps to ensure data consistency and provides clear error messages for invalid data.

#### **Schema Definitions**

-   **`account.py`**: Defines the schemas for bank accounts, including `AccountCreate`, `AccountUpdate`, and `Account`.
-   **`auth.py`**: Contains the schemas for authentication-related data, such as `UserRegister`, `UserLogin`, `RefreshTokenRequest`, and `AuthResponse`.
-   **`budget.py`**: Defines the schemas for budgets, including `BudgetCreate`, `BudgetUpdate`, and `Budget`.
-   **`category.py`**: Contains the schemas for transaction categories, including `CategoryCreate`, `CategoryUpdate`, and `Category`.
-   **`goal.py`**: Defines the schemas for financial goals, including `GoalCreate`, `GoalUpdate`, and `Goal`.
-   **`ml.py`**: Contains the schemas for the machine learning service, such as `MLCategorizationRequest` and `MLCategorizationResponse`.
-   **`transaction.py`**: Defines the schemas for transactions, including `TransactionCreate`, `TransactionUpdate`, and `Transaction`.
-   **`user.py`**: Contains the schemas for user data, such as `UserCreate`, `UserUpdate`, and `User`.
-   **`user_preferences.py`**: Defines the schemas for user preferences.

---

# Content from decision-log.md

# Knowledge Capture & Decision History

This document logs key design decisions, trade-offs, and future plans, based on the current state of the codebase.

## 1. Key Design Decisions

*   **Microservices-based Architecture:** The application is divided into several services (frontend, backend, ml-worker), which allows for independent development, deployment, and scaling.
*   **Containerization:** The use of Docker and Docker Compose ensures a consistent and reproducible environment for all services.
*   **Asynchronous ML Processing:** The use of Celery for ML tasks ensures that the main API remains responsive, even when processing a large number of transactions.

## 2. Trade-offs

*   **Complexity:** A microservices-based architecture can be more complex to manage than a monolithic application.
*   **Development Overhead:** The use of multiple services and technologies can increase the development overhead.

## 3. Known Limitations

*   **Scalability:** While the architecture is designed to be scalable, the current implementation may have limitations that need to be addressed in the future.
*   **Security:** The security of the application can always be improved. Further security audits and penetration testing should be conducted.

## 4. Planned Improvements

*   **Enhanced Analytics:** Implement more advanced analytics and data visualization features.
*   **Mobile App:** Develop a native mobile app for iOS and Android.
*   **Investment Tracking:** Add support for tracking investments and retirement accounts.

---

# Content from deployment.md



---

# Content from docker_configuration.md

### Docker Configuration Analysis

The project utilizes Docker and Docker Compose to containerize its various services, providing isolated, reproducible, and scalable environments for development and production.

#### 1. Docker Compose (`docker-compose.yml` and `docker-compose.dev.yml`)

The project uses two main Docker Compose files:
*   **`docker-compose.yml`**: This is the primary configuration for the full application stack, suitable for both development and production (though `docker-compose.dev.yml` overrides some settings for development). It defines the services, networks, and volumes.
*   **`docker-compose.dev.yml`**: This file is intended for local development. It overrides specific settings from `docker-compose.yml` to facilitate a faster and more convenient development workflow (e.g., enabling hot-reloading, mounting local code for live updates).

**Common Services Defined:**

*   **`postgres`**:
    *   **Image**: `postgres:15-alpine` (lightweight Alpine-based PostgreSQL image).
    *   **Restart Policy**: `unless-stopped`.
    *   **Environment Variables**: Configures `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` using environment variables, with default values provided.
    *   **Volumes**:
        *   `postgres_data:/var/lib/postgresql/data`: Persistent volume for database data.
        *   `./backend/init.sql:/docker-entrypoint-initdb.d/init.sql`: Initializes the database with a custom SQL script on first startup.
    *   **Ports**: Maps container port `5432` to host port `5432`.
    *   **Healthcheck**: Ensures the PostgreSQL service is ready before dependent services start.
    *   **Network**: Connected to `finance-network`.
*   **`redis`**:
    *   **Image**: `redis:7-alpine` (lightweight Alpine-based Redis image).
    *   **Restart Policy**: `unless-stopped`.
    *   **Ports**: Maps container port `6379` to host port `6379`.
    *   **Volumes**: `redis_data:/data`: Persistent volume for Redis data.
    *   **Command**: `redis-server --appendonly yes` to enable persistence.
    *   **Healthcheck**: Ensures the Redis service is ready.
    *   **Network**: Connected to `finance-network`.
*   **`backend`**:
    *   **Build Context**: `./backend` with `Dockerfile`.
    *   **Restart Policy**: `unless-stopped`.
    *   **Volumes**:
        *   `./backend:/app:cached`: Mounts the local backend code into the container for development (cached for performance).
        *   `./ml_models:/app/ml_models:cached`: Mounts ML models for the backend to access.
    *   **Ports**: Maps container port `8000` to host port `8000`.
    *   **Environment Variables**: Configures database URL, Redis URL, secret keys, Supabase credentials, Plaid API keys, and logging levels. Uses environment variables for sensitive data and configuration.
    *   **Command**: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` (in `docker-compose.dev.yml`, `--reload` is explicitly added for hot-reloading).
    *   **Dependencies**: Depends on `postgres` and `redis` being healthy.
    *   **Network**: Connected to `finance-network`.
*   **`frontend`**:
    *   **Build Context**: `./frontend` with `Dockerfile` (targeting `dev` stage in `docker-compose.yml` for development).
    *   **Restart Policy**: `unless-stopped`.
    *   **Volumes**:
        *   `./frontend:/app:cached`: Mounts local frontend code.
        *   `frontend_node_modules:/app/node_modules`: Uses a named volume for `node_modules` to prevent host `node_modules` from interfering and to speed up builds.
    *   **Ports**: Maps container ports `3000` and `3001` to host ports `3000` and `3001` (for Vite development server).
    *   **Environment Variables**: Sets `VITE_API_URL` to point to the backend service, `NODE_ENV`, and `CHOKIDAR_USEPOLLING` (for hot-reloading in WSL/Docker environments).
    *   **Command**: `npm run dev` to start the Vite development server.
    *   **Dependencies**: Depends on `backend`.
    *   **Network**: Connected to `finance-network`.
*   **`ml-worker`**:
    *   **Build Context**: `./ml-worker` with `Dockerfile`.
    *   **Restart Policy**: `unless-stopped`.
    *   **Volumes**:
        *   `./ml-worker:/app:cached`: Mounts local ML worker code.
        *   `./ml_models:/app/models:cached`: Mounts ML models for the worker to access.
    *   **Ports**: Maps container port `8001` to host port `8001` (though the `Dockerfile` CMD runs Celery, not a web server on this port directly).
    *   **Environment Variables**: Configures database URL, Redis URL, and logging levels.
    *   **Dependencies**: Depends on `postgres` and `redis` being healthy.
    *   **Network**: Connected to `finance-network`.
*   **`nginx`**:
    *   **Image**: `nginx:alpine` (lightweight Alpine-based Nginx image).
    *   **Restart Policy**: `unless-stopped`.
    *   **Ports**: Maps host ports `80` and `443` to container ports `80` and `443` (for HTTP and HTTPS).
    *   **Volumes**:
        *   `./nginx/nginx.conf:/etc/nginx/nginx.conf:ro`: Mounts custom Nginx configuration.
        *   `./nginx/ssl:/etc/nginx/ssl:ro`: Mounts SSL certificates (read-only).
    *   **Dependencies**: Depends on `frontend` and `backend`.
    *   **Network**: Connected to `finance-network`.

**Volumes:**
*   `postgres_data`: For persistent PostgreSQL data.
*   `redis_data`: For persistent Redis data.
*   `frontend_node_modules`: To cache `node_modules` for faster frontend builds and to avoid host-container conflicts.

**Networks:**
*   `finance-network`: A custom bridge network is defined to allow all services to communicate with each other using their service names (e.g., `backend` can connect to `postgres` at `postgres:5432`).

#### 2. Dockerfiles

*   **`backend/Dockerfile`**:
    *   **Base Image**: `python:3.11-slim`.
    *   **Environment Variables**: Sets `PYTHONDONTWRITEBYTECODE`, `PYTHONUNBUFFERED`, and `PYTHONPATH`.
    *   **System Dependencies**: Installs `build-essential`, `libpq-dev`, `curl` for Python package compilation and database connectivity.
    *   **Python Dependencies**: Copies `requirements-prod.txt` and installs production dependencies.
    *   **User**: Creates a non-root user `appuser` for security and runs the application as this user.
    *   **Exposed Port**: `8000`.
    *   **Healthcheck**: Uses `curl` to check the `/health` endpoint of the Uvicorn server.
    *   **Command**: Runs `uvicorn` to start the FastAPI application.
*   **`frontend/Dockerfile`**:
    *   **Multi-stage Build**: Uses multiple stages (`base`, `deps`, `dev`, `builder`, `production`) for optimized builds.
    *   **`base`**: `node:20-alpine` as the base image.
    *   **`deps`**: Installs production-only `npm` dependencies.
    *   **`dev`**: Installs all `npm` dependencies (including dev dependencies) and sets up the environment for development (exposes port `3000`, runs `npm run dev`).
    *   **`builder`**: Installs all `npm` dependencies and runs `npm run build` to create production assets.
    *   **`production`**: Uses `nginx:alpine` as the base. Copies custom Nginx configuration and the built frontend assets. Exposes port `80` and starts Nginx.
*   **`ml-worker/Dockerfile`**:
    *   **Base Image**: `python:3.11-slim`.
    *   **Environment Variables**: Similar to backend, sets Python environment variables.
    *   **System Dependencies**: Installs `build-essential`, `libpq-dev`, `curl`, `software-properties-common`, `git` (likely for model downloading or specific ML libraries).
    *   **Python Dependencies**: Copies `requirements.txt` and installs all dependencies.
    *   **Directories**: Creates `/app/models` and `/app/data` directories.
    *   **User**: Creates a non-root user `worker` and runs the Celery worker as this user.
    *   **Healthcheck**: Uses a Python script to check if the ML classifier is operational.
    *   **Command**: Runs the Celery worker (`celery -A worker worker`) with specified log level, concurrency, and max tasks per child.

#### 3. Development vs. Production Considerations

*   **Development (`docker-compose.dev.yml`)**:
    *   **Hot-reloading**: `backend` and `frontend` services use `volumes` to mount local code, and their `command` includes `--reload` or `npm run dev` to enable hot-reloading.
    *   **Node Modules**: `frontend_node_modules` volume is used to manage `node_modules` inside the container, preventing issues with host-mounted `node_modules`.
    *   **Debug Environment**: `DEBUG=true` and `LOG_LEVEL=debug` are set for the backend.
*   **Production (`docker-compose.yml` and Dockerfiles)**:
    *   **Optimized Builds**: Frontend uses a multi-stage Dockerfile to create a small Nginx image with only static assets. Backend installs `requirements-prod.txt` for production dependencies.
    *   **Nginx**: An Nginx service is included to act as a reverse proxy, serving the frontend static files and proxying API requests to the backend. This is crucial for production deployments for performance, SSL termination, and load balancing.
    *   **Persistent Data**: Named volumes (`postgres_data`, `redis_data`) ensure that database and Redis data persist across container restarts.
    *   **Security**: Non-root users (`appuser`, `worker`) are created and used in Dockerfiles.
    *   **Health Checks**: Robust health checks are defined for database and Redis to ensure dependencies are ready.

This Docker setup provides a comprehensive and flexible solution for managing the finance tracker application's microservices, catering to both development efficiency and production robustness.


---

# Content from frontend.md

# Frontend Architecture and Design

This document provides a comprehensive analysis of the finance tracker application's frontend architecture, design patterns, and key implementation details.

## 1. Application Architecture Overview

The finance tracker frontend is a modern single-page application (SPA) built with **React** and **TypeScript**. It leverages a robust set of libraries and patterns to ensure a scalable, maintainable, and responsive user experience.

*   **Core Framework**: React (with Vite for fast development).
*   **Language**: TypeScript for strong typing and improved code quality.
*   **Routing**: `react-router-dom` for declarative client-side navigation.
*   **State Management**:
    *   **React Query (`@tanstack/react-query`)**: Primary tool for server-state management (data fetching, caching, synchronization, and mutations). It significantly reduces boilerplate for data operations and provides powerful caching mechanisms.
    *   **Zustand**: Lightweight and flexible state management library used for global client-side state, specifically for authentication (`authStore`) and real-time data (`realtimeStore`).
*   **UI Library**: Custom UI components built with **Tailwind CSS** for styling, promoting consistency and rapid development.
*   **API Communication**: A custom `apiClient` handles all interactions with the backend API, including authentication, token management, and structured error handling.
*   **Real-time Communication**: WebSockets are utilized for live updates, managed through a dedicated hook and Zustand store.
*   **Code Structure**: Organized into logical modules (`components`, `pages`, `hooks`, `services`, `stores`, `utils`, `types`) to enhance modularity and separation of concerns.

## 2. Component Structure and Patterns

The application follows a clear component-based architecture, with components organized by their purpose and domain.

*   **`App.tsx`**: The root component, responsible for setting up the global context providers (React Query, Toast), authentication initialization, and defining the main routing structure.
*   **`pages/`**: Contains top-level components that represent distinct views or screens of the application (e.g., `Dashboard`, `Transactions`, `Settings`, `Login`). These components often orchestrate data fetching and display other, smaller components.
*   **`components/`**: Houses reusable UI components. This directory is further subdivided into domain-specific folders:
    *   **`components/ui/`**: Fundamental, generic UI building blocks (e.g., `Button`, `Input`, `Card`, `Modal`, `LoadingSpinner`, `Toast`, `ThemeToggle`, `Alert`). These are highly reusable and styled with Tailwind CSS.
    *   **`components/accounts/`**: Components related to managing bank accounts (e.g., `AccountReconciliation`, `AccountSyncStatus`, `AccountsList`).
    *   **`components/auth/`**: Authentication-related forms (e.g., `LoginForm`, `RegisterForm`).
    *   **`components/budgets/`**: Components for budget management (e.g., `BudgetCard`, `BudgetForm`).
    *   **`components/categories/`**: Components for category selection (e.g., `CategorySelector`).
    *   **`components/common/`**: General-purpose components like `ErrorBoundary` (for UI error handling), `ProtectedRoute` (for route protection), and `AuthInitializer` (for app startup authentication checks).
    *   **`components/dashboard/`**: Specific widgets and charts for the dashboard (e.g., `CategoryPieChart`, `MonthlyComparisonChart`, `RealtimeDashboard`, `NotificationPanel`, `RealtimeTransactionFeed`).
    *   **`components/goals/`**: Components for managing financial goals (e.g., `GoalCard`, `GoalForm`, `GoalsDashboard`, `MilestoneNotification`).
    *   **`components/layout/`**: Defines the overall application layout and navigation (`Navigation`).
    *   **`components/plaid/`**: Integrates with the Plaid API for bank connections (`PlaidLink`, `AccountConnectionStatus`).
    *   **`components/transactions/`**: Components for transaction management (e.g., `CSVImport`, `MLCategoryFeedback`, `TransactionFilters`, `TransactionForm`, `TransactionList`).

## 3. State Management Implementation

The application employs a hybrid state management approach, combining React Query for server-state and Zustand for client-side global state.

### React Query (`@tanstack/react-query`)

*   **Purpose**: Manages asynchronous data operations (fetching, caching, invalidation, synchronization, and mutations) with the backend API. It eliminates the need for manual loading states, error handling, and complex data fetching logic in components.
*   **Configuration**: `services/queryClient.ts` sets up the `QueryClient` with default options for `staleTime`, `gcTime`, `retry` logic, and global error handling (e.g., logging out on 401 Unauthorized errors).
*   **Usage**: Custom hooks in `hooks/` (e.g., `useAccounts`, `useBudgets`, `useTransactions`) wrap `useQuery` and `useMutation` to provide domain-specific data access. These hooks define `queryKeys` for efficient caching and invalidation.
*   **Cache Management**: `hooks/useAuthCacheManagement.ts` ensures that the React Query cache is cleared when the user's authentication state changes (e.g., login, logout, user switch) to prevent stale data from being displayed.

### Zustand

*   **Purpose**: Manages global client-side state that is not directly tied to server data, or for real-time updates that need immediate reflection. It's lightweight and provides a simple API for creating stores.
*   **`stores/authStore.ts`**:
    *   **State**: `user` (User object), `isAuthenticated` (boolean), `isLoading` (boolean), `error` (string).
    *   **Actions**: `login`, `register`, `logout`, `refreshToken`, `updateUser`, `checkTokenExpiration`.
    *   **Persistence**: Uses `localStorage` to persist `user` and `isAuthenticated` state across browser refreshes.
*   **`stores/realtimeStore.ts`**:
    *   **State**: `isConnected`, `connectionStatus`, `recentTransactions`, `transactionUpdates`, `milestoneAlerts`, `goalCompletions`, `goalUpdates`, `notifications`, `budgetAlerts`.
    *   **Actions**: `updateConnectionStatus`, `addRecentTransaction`, `markTransactionsSeen`, `addNotification`, `markNotificationRead`, `handleWebSocketMessage` (main entry point for WebSocket events), etc.
    *   **Middleware**: `subscribeWithSelector` allows components to subscribe to specific state changes.
*   **`stores/themeStore.ts`**:
    *   **State**: `theme` (user preference: 'light' | 'dark' | 'auto'), `systemTheme` ('light' | 'dark'), `actualTheme` (resolved theme applied to DOM).
    *   **Actions**: `setTheme`, `initializeTheme`, `applyTheme`.
    *   **Persistence**: Stores `theme-preference` in `localStorage`.

## 4. API Integration Patterns

Frontend-backend communication is centralized and follows a structured pattern.

*   **`services/api.ts` (`ApiClient`)**:
    *   **Core Functionality**: This class is the central point for all HTTP requests. It wraps the native `fetch` API.
    *   **Authentication**: Automatically attaches `Authorization: Bearer <token>` headers to requests using tokens retrieved from `secureStorage`.
    *   **Token Refresh**: Implements a silent token refresh mechanism. If a 401 Unauthorized response is received and a refresh token is available, it attempts to refresh the access token before retrying the original request.
    *   **Error Handling**: Provides structured error handling, parsing API error responses into specific error types (`ValidationError`, `NetworkError`, `AuthError`, `BusinessError`, `SystemError`) for easier consumption by the application.
    *   **CSRF Protection**: Integrates with `csrfService` to include CSRF tokens in request headers.
    *   **Mocking**: Can operate in a "mock data" or "UI only" mode (`services/mockApiClient.ts`) for frontend development without a running backend.

*   **`services/base/BaseService.ts`**:
    *   **Abstraction Layer**: Provides a base class for all domain-specific services. It encapsulates common API interaction logic (e.g., `get`, `post`, `put`, `delete`, `getPaginated`, `postFormData`, `getBlob`).
    *   **Caching**: Includes a basic in-memory caching mechanism for GET requests, which can be enabled per request.
    *   **Error Propagation**: Standardizes error handling by catching `ApiClient` errors and re-throwing them with additional service-specific context.

*   **Domain-Specific Services (`services/*.ts`)**:
    *   Classes like `AccountService`, `BudgetService`, `CategoryService`, `TransactionService`, `PlaidService`, `GoalService`, `UserPreferencesService`, and `MLService` extend `BaseService`.
    *   Each service defines methods for CRUD operations and other domain-specific interactions with their respective backend endpoints. They handle data serialization/deserialization and type conversions (e.g., cents to dollars).

## 5. Routing and Navigation

The application uses `react-router-dom` for navigation, providing a smooth single-page application experience.

*   **`App.tsx`**: The main routing configuration is defined here using `BrowserRouter`, `Routes`, and `Route` components.
*   **Protected Routes**: Most application routes (e.g., `/dashboard`, `/transactions`) are wrapped within a `ProtectedRoute` component.
*   **`components/common/ProtectedRoute.tsx`**: This component checks the user's authentication status (`useIsAuthenticated` from `authStore`). If the user is not authenticated, they are redirected to the `/login` page. A loading spinner is shown while the authentication status is being determined.
*   **Navigation (`components/layout/Navigation.tsx`)**: Provides the main application navigation links, using `NavLink` from `react-router-dom` to highlight the active route. It also displays user information and a logout button.

## 6. Key Areas - Detailed Breakdown

### Components

*   **`components/ui/`**:
    *   **Purpose**: Provides a consistent and reusable set of basic UI elements.
    *   **Examples**: `Button` (with variants, sizes, loading states), `Input` (with labels, error messages), `Card` (for content grouping), `Modal` (for overlays), `LoadingSpinner` (for visual feedback), `Toast` (for transient messages), `ThemeToggle` (for dark/light mode).
    *   **Styling**: All components are styled using Tailwind CSS classes, often combined with `clsx` and `tailwind-merge` for conditional styling.
*   **Domain-Specific Components**: Each domain (accounts, budgets, transactions, etc.) has its own folder within `components/` containing components specific to that domain's UI and functionality. These components often consume data from custom hooks and interact with services.

### Pages/Views

*   **Purpose**: Represent the main screens of the application. They typically compose multiple smaller components and orchestrate data flow for that specific view.
*   **Examples**:
    *   `Dashboard.tsx`: Displays an overview of financial data, including charts (`CategoryPieChart`, `MonthlyComparisonChart`), real-time transaction feeds (`RealtimeTransactionFeed`), and notifications (`NotificationPanel`). It uses `useDashboardAnalytics` and `useRealtimeStore`.
    *   `Transactions.tsx`: Manages all user transactions. It includes `TransactionFilters`, `TransactionList`, `TransactionForm` (for add/edit), and `CSVImport`. It heavily relies on `useTransactions` and `useTransactionActions`.
    *   `Settings.tsx`: Allows users to customize their application preferences, using `useUserPreferences` and `usePreferencesActions`.

### Services/API

*   **Purpose**: Encapsulate all logic for interacting with the backend API. They provide a clean, type-safe interface for components and hooks to fetch and manipulate data.
*   **Core**: `api.ts` (`ApiClient`) is the HTTP client.
*   **Base**: `base/BaseService.ts` provides common methods and error handling.
*   **Domain-Specific**: `accountService.ts`, `budgetService.ts`, `categoryService.ts`, `dashboardService.ts`, `goalService.ts`, `plaidService.ts`, `transactionService.ts`, `userPreferencesService.ts`, `mlService.ts`. Each service maps to a specific backend domain and exposes methods for data operations.
*   **Standardization**: `ServiceRegistry.ts` and `standardized/` services (`StandardizedTransactionService`, `StandardizedBudgetService`) are being introduced to provide a more consistent and robust service layer with explicit success/error results.

### State Management (Zustand Stores)

*   **`stores/authStore.ts`**:
    *   **State**: `user` (User object), `isAuthenticated` (boolean), `isLoading` (boolean), `error` (string).
    *   **Actions**: `login`, `register`, `logout`, `refreshToken`, `updateUser`, `checkTokenExpiration`.
    *   **Persistence**: Uses `localStorage` to persist `user` and `isAuthenticated` state across sessions.
*   **`stores/realtimeStore.ts`**:
    *   **State**: `isConnected`, `connectionStatus`, `recentTransactions`, `transactionUpdates`, `milestoneAlerts`, `goalCompletions`, `goalUpdates`, `notifications`, `budgetAlerts`.
    *   **Actions**: `updateConnectionStatus`, `addRecentTransaction`, `markTransactionsSeen`, `addNotification`, `markNotificationRead`, `handleWebSocketMessage` (main entry point for WebSocket events), etc.
    *   **Middleware**: `subscribeWithSelector` allows components to subscribe to specific state changes.
*   **`stores/themeStore.ts`**:
    *   **State**: `theme` (user preference: 'light' | 'dark' | 'auto'), `systemTheme` ('light' | 'dark'), `actualTheme` (resolved theme applied to DOM).
    *   **Actions**: `setTheme`, `initializeTheme`, `applyTheme`.
    *   **Persistence**: Stores `theme-preference` in `localStorage`.

### Hooks

*   **Purpose**: Encapsulate reusable logic, often integrating with React Query or Zustand, to provide data and functionality to components.
*   **Data Fetching Hooks (`hooks/useAccounts.ts`, `useBudgets.ts`, etc.)**:
    *   Wrap `useQuery` and `useMutation` from React Query.
    *   Define `queryKey` arrays for caching.
    *   Handle `onSuccess` and `onError` callbacks for cache invalidation and side effects (e.g., showing toasts).
*   **Authentication Hooks**: `useAuthUser`, `useIsAuthenticated`, `useAuthLoading`, `useAuthError` are selector hooks from `authStore` for efficient state access.
*   **Real-time Hooks**: `useWebSocket.ts` manages the WebSocket connection. Selector hooks from `realtimeStore` (e.g., `useConnectionStatus`, `useRealtimeTransactions`, `useNotifications`) provide access to real-time data.
*   **Utility Hooks**:
    *   `useAuthCacheManagement.ts`: Clears React Query cache on auth state changes.
    *   `usePlaidActions.ts`: Combines Plaid-related mutations (`exchangeToken`, `syncTransactions`, `syncBalances`).
    *   `useTransactionActions.ts`: Combines transaction-related mutations (CRUD, import, export).
    *   `useUserPreferences.ts`: Provides access to user preferences and actions to update them.

### Utils

*   **Purpose**: Provide general-purpose helper functions that are not tied to specific React components or API services.
*   **Examples**:
    *   `cn.ts`: A helper for conditionally combining Tailwind CSS classes.
    *   `currency.ts`: Functions for converting between cents and dollars, and formatting currency for display.
    *   `validation.ts`: Utility functions for validating various data types (emails, UUIDs, dates, amounts).
    *   `index.ts`: Re-exports common utilities.
    *   `envValidation.ts`: Validates environment variables at application startup.
    *   `formatDate`, `formatRelativeTime`, `debounce`, `generateId`, `truncate`, `isEmpty`: General utility functions for common tasks.

### Types

*   **Purpose**: Define the shape of data used throughout the application, ensuring type safety and improving code readability and maintainability.
*   **Location**: Primarily in the `types/` directory, with separate files for different domains (e.g., `auth.ts`, `transaction.ts`, `category.ts`, `budgets.ts`, `goals.ts`, `api.ts`, `errors.ts`, `websocket.ts`, `ml.ts`).
*   **Content**: Includes interfaces for API request/response bodies, domain models, state structures, and utility types.
*   **Error Types**: A comprehensive error type system (`errors.ts`) defines various categories of errors (validation, network, auth, business, system) for structured error handling.
*   **WebSocket Types**: Detailed type definitions for WebSocket messages (`websocket.ts`) ensure type-safe handling of real-time events.


---

# Content from glossary.md

# Glossary & Domain Knowledge

This document defines key terms, abbreviations, and concepts used throughout the project, based on the current state of the codebase.

## 1. Financial Terms

*   **Transaction:** A record of a financial event.
*   **Budget:** A plan for spending money over a period of time.
*   **Category:** A label used to group similar transactions.
*   **Goal:** A financial target that a user wants to achieve.

## 2. Machine Learning Jargon

*   **Embedding:** A numerical representation of text.
*   **Sentence Transformer:** A type of machine learning model that is used to generate embeddings for sentences.
*   **ONNX (Open Neural Network Exchange):** A format for representing machine learning models.

## 3. Internal Abbreviations

*   **PWA:** Progressive Web App
*   **JWT:** JSON Web Token
*   **ORM:** Object-Relational Mapping

## 4. External Service Integrations

*   **Plaid:** Used for connecting to users' bank accounts.
*   **SendGrid:** Used for sending emails.
*   **Supabase:** Used for authentication and as a hosted PostgreSQL database.

---

# Content from machine-learning.md

# Machine Learning Pipeline

This document outlines the architecture and implementation of the machine learning pipeline for intelligent transaction categorization, based on the current state of the codebase.

## 1. ML Pipeline Overview

The ML pipeline is designed for asynchronous processing of transaction categorization tasks using a Celery worker.

![ML Pipeline Diagram](./images/ml-pipeline.png)
*Figure 3: Machine Learning Pipeline*

### Pipeline Stages

1.  **Task Trigger:** When a new transaction is created, a Celery task is created to categorize it.
2.  **ML Worker:** A dedicated Celery worker picks up the task and uses a pre-trained Sentence Transformer model to generate an embedding for the transaction description.
3.  **Classification:** The transaction embedding is compared to pre-defined category embeddings to find the best match.
4.  **Database Update:** The categorized transaction is updated in the database.

## 2. Model Details

*   **Model:** `all-MiniLM-L6-v2` (Sentence Transformer)
*   **Location:** The model is stored in the `ml-worker/models` directory.

## 3. ML Worker

*   The `ml-worker` service is a Celery worker that is responsible for running the ML tasks.
*   It uses the `ml_classification_service.py` to perform the transaction categorization.

## 4. ONNX and Optimization

*   The `onnx_converter.py` and `optimized_inference_engine.py` files suggest that the project is set up to use ONNX for optimized model inference, which can significantly improve performance.

---

# Content from ml_worker.md

### ML Worker Analysis

The `ml-worker` directory contains the core components for the machine learning service responsible for transaction categorization. It leverages modern ML techniques, including sentence transformers, ONNX for optimized inference, and a robust production orchestration system with A/B testing and monitoring.

#### 1. Core Components and Technologies

*   **`ml_classification_service.py`**: This is the heart of the ML worker. It implements the `TransactionClassifier` class, which performs transaction categorization.
    *   **Sentence Transformers**: Uses `all-MiniLM-L6-v2` for generating embeddings of transaction descriptions. This model is downloaded and stored locally.
    *   **Few-shot Learning**: Initializes category prototypes by averaging embeddings of example transactions for each category. This allows the model to categorize new transactions by finding the closest prototype in the embedding space.
    *   **Cosine Similarity**: Uses cosine similarity to determine the closeness between a transaction embedding and category prototypes.
    *   **Confidence Levels**: Assigns confidence levels (low, medium, high) based on the similarity score.
    *   **User Feedback**: Collects user feedback to improve model accuracy over time.
    *   **ONNX Export**: Supports exporting the model to ONNX format for optimized inference.
    *   **Quantization**: Integrates with ONNX Runtime to perform INT8 quantization (dynamic and static) for further performance gains and reduced model size.
*   **`optimized_inference_engine.py`**: Implements `OptimizedInferenceEngine` for high-performance, low-latency inference.
    *   **ONNX Runtime**: Utilizes ONNX Runtime for CPU-optimized inference.
    *   **Batch Processing**: Supports batch classification for higher throughput.
    *   **Embedding Cache**: Caches embeddings of frequently encountered texts to reduce redundant computations.
    *   **CPU Optimization**: Includes settings for CPU affinity and thread management to maximize performance.
    *   **Performance Benchmarking**: Provides methods to benchmark the inference performance of different model versions.
*   **`production_orchestrator.py`**: The `ProductionOrchestrator` class manages the entire ML pipeline in a production environment.
    *   **Model Deployment**: Handles loading and managing different model variants (e.g., base, ONNX, quantized).
    *   **Monitoring Integration**: Integrates with `ModelMonitor` to record and track inference metrics.
    *   **A/B Testing Integration**: Integrates with `ABTestingFramework` to conduct A/B tests between different model variants in a live environment.
    *   **Performance Targets**: Defines and checks against performance targets (e.g., max inference time, min accuracy, min throughput).
    *   **Readiness Checks**: Performs checks to ensure the system is ready for production.
*   **`model_monitoring.py`**: The `ModelMonitor` class provides comprehensive real-time monitoring and alerting for ML models.
    *   **Prometheus Integration**: Exposes metrics (inference time, predictions, accuracy, memory, CPU usage, error rate, cache hit rate) via Prometheus.
    *   **Alerting**: Defines thresholds for various metrics and triggers alerts (warning, critical) if these thresholds are breached.
    *   **Performance Snapshots**: Provides snapshots of current model performance.
    *   **System Metrics**: Collects system-level metrics like CPU and memory usage.
*   **`ab_testing_framework.py`**: Implements an A/B testing framework for ML models.
    *   **Experiment Management**: Allows creation, starting, and stopping of experiments.
    *   **Traffic Splitting**: Supports different strategies for assigning users to model variants (random, user ID hash, time-based).
    *   **Result Recording**: Records experiment results, including predictions, confidence, inference time, and user feedback.
    *   **Statistical Analysis**: Performs statistical tests (e.g., t-tests, z-tests) to compare variant performance on success metrics (accuracy, inference time).
    *   **Guard Rails**: Implements safety thresholds to automatically pause or stop experiments if performance degrades significantly.
    *   **Reporting**: Generates comprehensive experiment reports with recommendations.
*   **`onnx_converter.py`**: Handles the conversion of Sentence Transformer models to ONNX format and applies quantization.
    *   **ONNX Export**: Exports PyTorch models to ONNX.
    *   **Optimization**: Applies ONNX graph optimizations.
    *   **Dynamic Quantization**: Performs dynamic INT8 quantization.
    *   **Static Quantization**: Performs static INT8 quantization using calibration data for higher accuracy.
    *   **Benchmarking**: Compares the performance of original PyTorch, ONNX, and quantized ONNX models.
    *   **Validation**: Validates the ONNX model's output against the original PyTorch model.
*   **`worker.py`**: This is the Celery worker entry point.
    *   **Celery Integration**: Configures and runs the Celery worker, defining tasks for transaction classification, feedback collection, model updates, and health checks.
    *   **Asynchronous Processing**: All ML tasks are executed asynchronously via Celery, allowing the main application to remain responsive.
    *   **Production Orchestrator Initialization**: Initializes the `ProductionOrchestrator` on worker startup, setting up the entire ML serving pipeline.
    *   **Fallback Mechanism**: Includes a fallback to a basic classifier if the production orchestrator fails to initialize.
*   **`Dockerfile`**: Defines the Docker image for the ML worker.
    *   **Python 3.11-slim**: Uses a lightweight Python base image.
    *   **Dependencies**: Installs system dependencies (build-essential, libpq-dev, curl, git) and Python dependencies from `requirements.txt`.
    *   **Work Directory**: Sets `/app` as the working directory.
    *   **Non-root User**: Runs the worker as a non-root user (`worker`) for security.
    *   **Health Check**: Includes a health check to ensure the Celery worker and classifier are operational.
    *   **CMD**: Runs the Celery worker with specified concurrency and logging levels.
*   **`requirements.txt`**: Lists all Python dependencies for the ML worker, including `scikit-learn`, `pandas`, `numpy`, `sentence-transformers`, `transformers`, `torch`, `onnx`, `onnxruntime`, `celery`, `redis`, `sqlalchemy`, `psycopg2-binary`, `prometheus-client`, `psutil`, and `scipy`.
*   **`download_model.py`**: A utility script to download the `all-MiniLM-L6-v2` sentence transformer model locally.

#### 2. Data Flow and Interactions

1.  **Model Training/Update**:
    *   The `ml_classification_service.py` initializes `category_prototypes` from default examples.
    *   User feedback (`collect_feedback` task) and new category examples (`add_category_example` task) are collected.
    *   The model can be updated (`update_model_from_feedback` task) by recomputing prototypes based on this feedback.
    *   Prototypes are persisted using `pickle` files (`models/category_prototypes.pkl`).
2.  **Model Optimization and Deployment**:
    *   The `onnx_converter.py` converts the PyTorch `SentenceTransformer` model to ONNX format (`export_model_to_onnx` task).
    *   It then applies dynamic or static INT8 quantization to the ONNX model.
    *   These optimized ONNX models are stored in `models/production/`.
3.  **Production Orchestration**:
    *   On worker startup, `worker.py` initializes the `ProductionOrchestrator`.
    *   The orchestrator loads the optimized ONNX models into `OptimizedInferenceEngine` instances.
    *   It runs initial performance benchmarks on all loaded models.
    *   If A/B testing is enabled, it sets up an experiment using `ab_testing_framework.py`, assigning traffic to different model variants.
    *   `model_monitoring.py` starts collecting real-time metrics and checking for alerts.
4.  **Transaction Classification (Inference)**:
    *   When a `classify_transaction` task is received by Celery, the `ProductionOrchestrator` determines which model variant to use (based on A/B test assignment).
    *   The selected `OptimizedInferenceEngine` performs the classification, leveraging ONNX Runtime, batch processing, and caching for low-latency inference.
    *   Inference results (predicted category, confidence, inference time) are returned.
5.  **Monitoring and Feedback Loop**:
    *   Inference metrics are recorded by `ModelMonitor`.
    *   User feedback on categorization is collected (`collect_user_feedback` task) and used to improve the model over time, closing the feedback loop.
    *   A/B test results are recorded and analyzed by `ab_testing_framework.py`.

#### 3. Key Features and Architectural Patterns

*   **Microservices Architecture**: The ML worker is a separate service (Celery worker) that communicates asynchronously with the main backend, promoting loose coupling and scalability.
*   **Asynchronous Processing**: Celery is used for all ML tasks, ensuring that long-running operations (like model inference or training) do not block the main application.
*   **Model Optimization**: Extensive use of ONNX and quantization for highly efficient, low-latency inference on CPU.
*   **Few-shot Learning**: Enables the model to adapt to new categories or user-specific nuances with minimal examples, reducing the need for large, labeled datasets.
*   **A/B Testing**: Built-in framework for comparing different model versions or configurations in a live production environment, allowing data-driven decisions on model deployment.
*   **Real-time Monitoring**: Integration with Prometheus for continuous monitoring of model performance, resource utilization, and error rates, enabling proactive issue detection and alerting.
*   **Feedback Loop**: A clear mechanism for collecting user feedback and using it to retrain/update the model, ensuring continuous improvement.
*   **Containerization**: Dockerfile provides a reproducible and isolated environment for deploying the ML worker.
*   **Production Readiness**: The `ProductionOrchestrator` encapsulates complex logic for model loading, variant management, and integration with monitoring and A/B testing, making the ML service production-ready.

This ML worker is a sophisticated system designed for high-performance, continuously improving transaction categorization, with robust tools for deployment, monitoring, and experimentation.


---

# Content from operational-notes.md

# Operational Notes

This document provides essential information for operating, maintaining, and troubleshooting the Finance Tracker application. It covers development setup, environment configurations, build/deployment processes, and key operational considerations.

## 1. Development Setup

The project is designed for easy local development using Docker Compose. The primary entry point for starting the entire stack is the `scripts/dev.sh` script.

### Quick Start

1.  **Clone the repository**:
    ```bash
    git clone <repo-url>
    cd finance-tracker
    ```
2.  **Start development environment**:
    ```bash
    ./scripts/dev.sh
    ```
    This script will automatically copy `.env.example` to `.env` and start all services using Docker Compose.

### Access Points

Once the services are up, you can access the application components at:

*   **Frontend**: `http://localhost:3000` (with hot reload)
*   **Backend API**: `http://localhost:8000` (with auto-reload)
*   **API Docs**: `http://localhost:8000/docs` (Swagger UI, always enabled)
*   **PostgreSQL**: `localhost:5432` (database: `finance_tracker_dev`)
*   **Redis**: `localhost:6379`
*   **ML Worker**: `http://localhost:8001` (Celery worker, not a web server, but accessible for internal communication)

### Common Development Commands

*   **Stop all services**:
    ```bash
    docker-compose down
    ```
*   **Fresh restart (clears volumes)**:
    ```bash
    docker-compose down -v && ./scripts/dev.sh
    ```
*   **View logs for a service**:
    ```bash
    docker-compose logs -f [service-name]
    # Example: docker-compose logs -f backend
    ```
*   **Shell access to a service**:
    ```bash
    docker-compose exec [service-name] bash
    # Example: docker-compose exec backend bash
    ```

## 2. Environment Variables

Environment variables are crucial for configuring the application across different environments. They are primarily defined in `docker-compose.yml` and `docker-compose.dev.yml`, often loaded from a `.env` file.

### Backend Service (`backend/`)

*   `DATABASE_URL`: PostgreSQL connection string (e.g., `postgresql://user:password@host:port/database`).
*   `REDIS_URL`: Redis connection string (e.g., `redis://redis:6379`).
*   `SECRET_KEY`: A strong, random key for general application security.
*   `JWT_SECRET_KEY`: A strong, random key for JWT token signing.
*   `SUPABASE_URL`: URL for Supabase integration.
*   `SUPABASE_ANON_KEY`: Anonymous key for Supabase integration.
*   `ENVIRONMENT`: Application environment (`development`, `staging`, `production`).
*   `DEBUG`: `true` or `false`. Enables/disables debug mode (detailed error messages).
*   `LOG_LEVEL`: Logging verbosity (`debug`, `info`, `warning`, `error`).
*   `ENABLE_PLAID`: `true` or `false`. Enables/disables Plaid integration.
*   `PLAID_CLIENT_ID`: Plaid API client ID.
*   `PLAID_SECRET`: Plaid API secret.
*   `PLAID_ENV`: Plaid environment (`sandbox`, `development`, `production`).
*   `PLAID_PRODUCTS`: Comma-separated list of Plaid products (e.g., `transactions,accounts`).
*   `PLAID_COUNTRY_CODES`: Comma-separated list of country codes for Plaid (e.g., `US`).

### Frontend Service (`frontend/`)

*   `VITE_API_URL`: URL of the backend API (e.g., `http://localhost:8000/api`).
*   `VITE_APP_NAME`: Application display name.
*   `VITE_APP_VERSION`: Application version.
*   `VITE_ENABLE_DEVTOOLS`: `true` or `false`. Enables/disables development tools.
*   `VITE_ADMIN_BYPASS`: `true` or `false`. Enables/disables admin bypass for authentication (development only).
*   `NODE_ENV`: Node.js environment (`development`, `production`).
*   `CHOKIDAR_USEPOLLING`: `true` or `false`. Used for hot-reloading in certain Docker/WSL setups.

### ML Worker Service (`ml-worker/`)

*   `REDIS_URL`: Redis connection string (same as backend).
*   `DATABASE_URL`: PostgreSQL connection string (same as backend, used for fetching training data or storing feedback).
*   `ENVIRONMENT`: Application environment.
*   `DEBUG`: `true` or `false`.

### Database (`postgres`)

*   `POSTGRES_DB`: Database name.
*   `POSTGRES_USER`: Database user.
*   `POSTGRES_PASSWORD`: Database password.

## 3. Build and Deployment Process

The project uses a GitHub Actions CI/CD pipeline (`ci.yml`) to automate building, testing, and deployment.

### Continuous Integration (CI)

On every `push` to `main` or `develop` branches, and on every `pull_request`:

1.  **Checkout code**.
2.  **Build and Test Backend**:
    *   Sets up Python 3.11.
    *   Installs Poetry and backend dependencies (`poetry install --no-root`).
    *   Runs backend tests (`poetry run pytest`).
    *   Runs backend linting (`poetry run ruff check .`).
3.  **Build and Test Frontend**:
    *   Sets up Node.js 20.
    *   Installs frontend dependencies (`npm ci`).
    *   Runs frontend tests (`npm test`).
    *   Runs frontend linting (`npm run lint`).
    *   Builds the frontend for production (`npm run build`).
4.  **Build and Test ML Worker**:
    *   Sets up Python 3.11.
    *   Installs ML worker dependencies (`pip install -r requirements.txt`).
    *   Downloads the ML model (`python download_model.py`).
    *   (Placeholder for ML worker tests).

### Continuous Deployment (CD)

If all CI jobs pass and the `push` is to the `main` branch:

1.  **Login to Docker Hub** (using GitHub Secrets for credentials).
2.  **Build and Push Docker Images**: Uses `docker-compose build` and `docker-compose push` to build and push all service images to Docker Hub.
3.  **Deploy to Production (Placeholder)**: This step is a placeholder for actual deployment commands (e.g., SSH into a server, run `docker-compose pull`, update services).

## 4. Maintenance and Troubleshooting

### Logging

*   **Backend**: Configured with `LOG_LEVEL` environment variable. Logs are output to `stdout`/`stderr` and can be viewed using `docker-compose logs -f backend`.
*   **ML Worker**: Celery worker logs are also output to `stdout`/`stderr` and can be viewed via `docker-compose logs -f ml-worker`.
*   **Frontend**: Console logs are available in the browser's developer tools.

### Health Checks

Each service has health checks defined in `docker-compose.yml`:

*   **PostgreSQL**: `pg_isready` command.
*   **Redis**: `redis-cli ping` command.
*   **Backend**: `curl -f http://localhost:8000/health` endpoint.
*   **ML Worker**: Python script checking classifier status.

Additionally, the Backend API exposes dedicated health endpoints:

*   `GET /health`: Basic API health.
*   `GET /health/detailed`: Detailed health of API and its dependencies (DB, Redis, Supabase).
*   `GET /health/db`: Database connection check.
*   `GET /health/auth`: Authentication service connection check.

### Database Migrations

*   **Alembic**: Used for managing database schema changes.
*   **Create a new migration**: From `backend/` directory: `poetry run alembic revision --autogenerate -m "your_migration_message"`.
*   **Apply migrations**: From `backend/` directory: `poetry run alembic upgrade head`.

### Linting and Formatting

*   **Backend**: Uses `ruff` for linting and formatting. Run with `poetry run ruff check .` and `poetry run ruff format .` from `backend/`.
*   **Frontend**: Uses `eslint`. Run with `npm run lint` from `frontend/`.

## 5. Security Considerations

### Development Environment

**WARNING**: The development setup has relaxed security settings for convenience. **DO NOT use this configuration in production.**

*   **Weak Secrets**: Uses predictable development keys (`devpassword123`, default secret keys).
*   **Debug Enabled**: Detailed error messages and logs are exposed.
*   **CORS Disabled**: Allows all origins for development.
*   **Admin Bypass**: Frontend includes an admin bypass button for testing without full authentication setup.

### Production Environment

*   **Strong Secrets**: All sensitive environment variables (database passwords, secret keys, API keys) must be replaced with strong, randomly generated values and managed securely (e.g., using Docker Secrets, Kubernetes Secrets, or a dedicated secrets management service).
*   **Nginx**: Acts as a reverse proxy for SSL termination and serving static files, enhancing security and performance.
*   **Non-root Users**: Services run as non-root users within their Docker containers.
*   **Firewall Rules**: Ensure only necessary ports are exposed to the internet.
*   **Regular Updates**: Keep base images and dependencies updated to patch security vulnerabilities.

This document should serve as a comprehensive guide for anyone involved in the operation and maintenance of the Finance Tracker application.


---

# Content from real-time-systems.md

# Real-time Systems

This document describes the real-time architecture of the application, based on the current state of the codebase.

## 1. Real-time Architecture Overview

The application uses WebSockets for real-time communication between the frontend and backend.

![Real-time Architecture Diagram](./images/real-time-architecture.png)
*Figure 4: Real-time System Architecture*

### Key Components

*   **FastAPI WebSocket Endpoints:** The backend exposes WebSocket endpoints for real-time communication.
*   **`useWebSocket` Hook:** The frontend uses a custom `useWebSocket` hook to connect to the WebSocket endpoints and handle incoming messages.
*   **Zustand `realtimeStore`:** The `realtimeStore` is used to manage the state of the WebSocket connection and the real-time data.

## 2. WebSocket Endpoints

*   The backend exposes a WebSocket endpoint at `/ws`.
*   The `backend/app/routes/websockets.py` file contains the logic for handling WebSocket connections.

## 3. Real-time Events

The `frontend/src/types/websocket.ts` file defines the types for the WebSocket events.

*   **`TRANSACTION_UPDATED`**: Sent when a transaction is updated.
*   **`BUDGET_UPDATED`**: Sent when a budget is updated.
*   **`GOAL_UPDATED`**: Sent when a goal is updated.

---

# Content from setup.md



---

