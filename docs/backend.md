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

-   **`plaid_orchestration_service.py` and related services**: The Plaid integration is now modularized into focused services: `plaid_client_service.py` (API communication), `plaid_account_service.py` (account management), `plaid_transaction_service.py` (transaction sync), and `plaid_webhook_service.py` (webhooks/recurring). The `plaid_orchestration_service.py` coordinates these services and maintains backward compatibility.
-   **`transaction_sync_service.py`**: This service is responsible for synchronizing transactions from Plaid into the application's database. It handles duplicate detection and ensures that the transaction data is consistent.
-   **`account_sync_monitor.py`**: This service monitors the status of account synchronization with Plaid, providing insights into the health of the connections.
-   **`automatic_sync_scheduler.py`**: This service manages the scheduling of automatic account synchronization with Plaid, ensuring that the user's data is kept up-to-date.
-   **`ml_service.py`**: This service acts as a client for the machine learning service. It provides a simple interface for categorizing transactions and submitting feedback to the ML model.

#### **Analytics and Insights Services**

-   **`analytics_service.py`**: This service is responsible for generating analytics data for the application, such as the data for the main dashboard.
-   **`account_insights_service.py`**: This service likely provides more advanced analytics and insights about user accounts, such as spending patterns and cash flow analysis.

#### **Utility Services**

-   **`reconciliation_service.py`**: This unified service handles comprehensive account balance reconciliation with intelligent discrepancy detection and resolution (merged from basic and enhanced versions).
-   **`transaction_import_service.py`**: This service is responsible for importing transactions from external sources, such as CSV files.

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

This router is responsible for managing user profiles.

-   **Profile Management**: Allows users to get and update their profile information.

-   **Search**: Provides an endpoint for searching for users.

##### `websockets.py`

This file defines the WebSocket endpoint for real-time communication with clients.

-   **Real-time Updates**: Handles WebSocket connections for sending real-time updates to clients, such as new transactions or budget alerts.
-   **Authentication and Subscriptions**: Includes logic for authenticating WebSocket connections and for managing subscriptions to different real-time events.

#### **Root Endpoint**

The application has a root endpoint `/` that returns basic information about the API, including its version, environment, and status.