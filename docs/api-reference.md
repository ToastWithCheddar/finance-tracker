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
*   **Response**: `Dict[str, Any]`
*   **Errors**: `422` (Validation Error), `409` (User already exists)

**`POST /auth/login`**
*   **Description**: Authenticates a user and returns access and refresh tokens.
*   **Request Body**: `UserLogin` schema
*   **Response**: `StandardAuthResponse`
*   **Errors**: `401` (Invalid credentials), `422` (Validation Error)

**`POST /auth/refresh`**
*   **Description**: Refreshes an expired access token using a refresh token.
*   **Request Body**: `RefreshTokenRequest` schema
*   **Response**: `StandardAuthResponse`
*   **Errors**: `401` (Invalid or expired refresh token)

**`GET /auth/me`**
*   **Description**: Retrieves the profile of the currently authenticated user.
*   **Authentication**: Required
*   **Response**: `User` schema
*   **Errors**: `401` (Unauthorized)

**`POST /auth/request-password-reset`**
*   **Description**: Initiates a password reset process.
*   **Request Body**: `{ "email": "user@example.com" }`
*   **Response**: `204 No Content`
*   **Errors**: `422` (Validation Error)

**`POST /auth/resend-verification`**
*   **Description**: Resends email verification link.
*   **Request Body**: `{ "email": "user@example.com" }`
*   **Response**: `204 No Content`
*   **Errors**: `422` (Validation Error)

**`GET /auth/health`**
*   **Description**: Health check for the authentication service.
*   **Authentication**: None
*   **Response**: `Dict[str, Any]`
*   **Errors**: `500` (Internal Server Error)

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

**`DELETE /users/me`**
*   **Description**: Deletes the currently authenticated user's account.
*   **Authentication**: Required
*   **Response**: `{ "message": "Account deactivated successfully" }`
*   **Errors**: `401` (Unauthorized)

**`GET /users/search`**
*   **Description**: Searches for users by query.
*   **Authentication**: Required
*   **Query Parameters**:
    *   `query` (string, required): Search query.
    *   `skip` (int, optional): Number of users to skip (default: 0).
    *   `limit` (int, optional): Maximum number of users to return (default: 20).
*   **Response**: `List[UserProfile]` schema
*   **Errors**: `401` (Unauthorized)

**`GET /users/{user_id}`**
*   **Description**: Retrieves a specific user's public profile by ID.
*   **Authentication**: Required
*   **Path Parameters**:
    *   `user_id` (UUID): The ID of the user.
*   **Response**: `UserProfile` schema
*   **Errors**: `401` (Unauthorized), `404` (User not found)

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

**`POST /users/me/preferences/reset`**
*   **Description**: Resets user preferences to default values.
*   **Authentication**: Required
*   **Response**: `UserPreferences` schema
*   **Errors**: `401` (Unauthorized)

**`GET /users/me/profile`**
*   **Description**: Retrieves the current user's public profile information.
*   **Authentication**: Required
*   **Response**: `UserProfile` schema
*   **Errors**: `401` (Unauthorized)

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
*   **Response**: `dict` (containing `items`, `total`, `page`, `per_page`, `pages`)
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
*   **Response**: `{ "message": "Transaction deleted successfully" }`
*   **Errors**: `401` (Unauthorized), `404` (Transaction not found)

**`POST /transactions/bulk-delete`**
*   **Description**: Deletes multiple transactions by their IDs.
*   **Authentication**: Required
*   **Request Body**: `{ "transaction_ids": ["uuid1", "uuid2"] }`
*   **Response**: `{ "message": "Successfully deleted X transactions", "deleted_count": int }`
*   **Errors**: `401` (Unauthorized), `422` (Validation Error)

**`POST /transactions/import`**
*   **Description**: Imports transactions from a CSV file.
*   **Authentication**: Required
*   **Request Body**: `multipart/form-data` with a `file` field containing the CSV.
*   **Response**: `{ "message": "Successfully imported X transactions", "imported_count": int }`
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
*   **Response**: `dict`
*   **Errors**: `401` (Unauthorized)

**`GET /transactions/analytics/dashboard`**
*   **Description**: Retrieves comprehensive dashboard analytics for the current user.
*   **Authentication**: Required
*   **Query Parameters**:
    *   `start_date` (datetime, optional): Start date for analytics period.
    *   `end_date` (datetime, optional): End date for analytics period.
*   **Response**: `dict`
*   **Errors**: `401` (Unauthorized)

**`GET /transactions/analytics/trends`**
*   **Description**: Retrieves spending trends over time.
*   **Authentication**: Required
*   **Query Parameters**:
    *   `period` (string, optional): Trend period (`weekly` or `monthly`, default: `monthly`).
*   **Response**: `List[Dict[str, Any]]`
*   **Errors**: `401` (Unauthorized)

**`GET /transactions/search_transactions`**
*   **Description**: Advanced search for transactions with multiple filters.
*   **Authentication**: Required
*   **Query Parameters**:
    *   `q` (string, required): Search query.
    *   `start_date` (datetime, optional): Start date filter.
    *   `end_date` (datetime, optional): End date filter.
    *   `category` (string, optional): Category filter.
    *   `transaction_type` (string, optional): Transaction type filter.
    *   `page` (int, optional): Page number (default: 1).
    *   `per_page` (int, optional): Items per page (default: 25).
*   **Response**: `dict`
*   **Errors**: `401` (Unauthorized)

**`GET /transactions/categories`**
*   **Description**: Retrieves all unique transaction categories for the current user.
*   **Authentication**: Required
*   **Response**: `List[str]`
*   **Errors**: `401` (Unauthorized)

### 5. Categories

**`GET /categories`**
*   **Description**: Retrieves a list of all categories (system-defined and user-defined).
*   **Authentication**: Required
*   **Query Parameters**:
    *   `skip` (int, optional): Number of categories to skip (default: 0).
    *   `limit` (int, optional): Maximum number of categories to return (default: 100).
    *   `include_system` (boolean, optional): Include system categories (default: true).
    *   `parent_only` (boolean, optional): Only return top-level categories.
    *   `search` (string, optional): Search categories by name.
*   **Response**: `List[Category]` schema
*   **Errors**: `401` (Unauthorized)

**`GET /categories/system`**
*   **Description**: Retrieves a list of all system (default) categories.
*   **Authentication**: None
*   **Response**: `List[Category]` schema
*   **Errors**: `500` (Internal Server Error)

**`GET /categories/my`**
*   **Description**: Retrieves a list of the current user's categories.
*   **Authentication**: Required
*   **Query Parameters**:
    *   `include_system` (boolean, optional): Include system categories (default: true).
*   **Response**: `List[Category]` schema
*   **Errors**: `401` (Unauthorized)

**`GET /categories/hierarchy`**
*   **Description**: Retrieves categories in a hierarchical structure.
*   **Authentication**: Required
*   **Query Parameters**:
    *   `include_system` (boolean, optional): Include system categories (default: true).
*   **Response**: `List[Category]` schema
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
*   **Response**: `{ "message": "Category deleted successfully" }`
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
    *   `skip` (int, optional): Number of budgets to skip (default: 0).
    *   `limit` (int, optional): Maximum number of budgets to return (default: 100).
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
    *   `skip` (int, optional): Number of goals to skip (default: 0).
    *   `limit` (int, optional): Maximum number of goals to return (default: 100).
*   **Response**: `GoalsResponse` schema
*   **Errors**: `401` (Unauthorized)

**`GET /goals/stats`**
*   **Description**: Retrieves overall statistics for financial goals.
*   **Authentication**: Required
*   **Response**: `GoalStats` schema
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

**`POST /goals/process-auto-contributions`**
*   **Description**: Processes automatic contributions for eligible goals.
*   **Authentication**: Required
*   **Response**: `{ "message": "string", "results": { "success": int, "failed": int } }`
*   **Errors**: `401` (Unauthorized)

**`GET /goals/types/options`**
*   **Description**: Retrieves available goal types and priorities for UI dropdowns.
*   **Authentication**: None
*   **Response**: `dict`
*   **Errors**: `500` (Internal Server Error)

### 8. AI Insights

**`GET /insights`**
*   **Description**: Retrieves a list of AI-generated financial insights for the authenticated user.
*   **Authentication**: Required
*   **Query Parameters**:
    *   `type` (string, optional): Filter by insight type (`spending_spike`, `savings_opportunity`, `budget_alert`, `spending_pattern`, `goal_progress`, `cashflow_analysis`, `recurring_expense`, `unusual_transaction`).
    *   `priority` (integer, optional): Filter by priority level (`1` = High, `2` = Medium, `3` = Low).
    *   `is_read` (boolean, optional): Filter by read status.
    *   `limit` (integer, optional): Number of insights to return (1-100, default: 30).
    *   `offset` (integer, optional): Offset for pagination (default: 0).
*   **Response**: `InsightListResponse` schema
*   **Errors**: `401` (Unauthorized)

**`PATCH /insights/{insight_id}`**
*   **Description**: Updates an insight (primarily for marking as read/unread).
*   **Authentication**: Required
*   **Path Parameters**:
    *   `insight_id` (UUID): The ID of the insight.
*   **Request Body**: `InsightUpdate` schema
*   **Response**: `InsightResponse` schema
*   **Errors**: `401` (Unauthorized), `404` (Insight not found)

**`DELETE /insights/{insight_id}`**
*   **Description**: Deletes a specific insight.
*   **Authentication**: Required
*   **Path Parameters**:
    *   `insight_id` (UUID): The ID of the insight.
*   **Response**: `{ "message": "Insight deleted successfully" }`
*   **Errors**: `401` (Unauthorized), `404` (Insight not found)

### 9. Machine Learning (ML)

**`POST /ml/categorize`**
*   **Description**: Categorizes a transaction using the ML model.
*   **Authentication**: Required
*   **Request Body**: `MLCategorizeRequest` schema
*   **Response**: `Dict[str, Any]`
*   **Errors**: `401` (Unauthorized), `422` (Validation Error)

**`POST /ml/feedback`**
*   **Description**: Submits user feedback to improve the ML model's categorization.
*   **Authentication**: Required
*   **Request Body**: `transaction_id: UUID, correct_category_id: UUID`
*   **Response**: `{ "success": True, "message": "Feedback submitted successfully" }`
*   **Errors**: `401` (Unauthorized), `422` (Validation Error)

**`GET /ml/health`**
*   **Description**: Retrieves the health status of the ML service.
*   **Authentication**: Required
*   **Response**: `Dict[str, Any]`
*   **Errors**: `401` (Unauthorized)

**`GET /ml/stats`**
*   **Description**: Retrieves ML usage statistics for the current user.
*   **Authentication**: Required
*   **Response**: `Dict[str, Any]`
*   **Errors**: `401` (Unauthorized)

### 10. Health Check

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
