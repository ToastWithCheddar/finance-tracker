## 1\. Project Mission & Core Philosophy

**Primary Mission:** To engineer and maintain a production-grade, modern personal finance application. The goal is to empower users with a comprehensive tool to track all their financial activities, set and achieve savings goals, manage budgets effectively, and receive clear, explainable, and actionable AI-powered insights into their spending habits.

#### Core Product Philosophy (Non-Negotiable Principles)

  * **User Empowerment and Control**: The application must always prioritize user agency. While AI and automation will handle tedious tasks, every suggestion, categorization, or insight is fully transparent and overridable by the user. The user is the ultimate authority.
  * **Radical Transparency**: There will be no "black box" algorithms. For every AI-driven feature, the system must be able to surface *why* a decision was made, including confidence scores and the data points that influenced the outcome.
  * **Privacy as a Foundation**: The system is built on a privacy-first architecture. No sensitive personal or financial data should leave the user's control (i.e., be sent to third-party servers for processing) without explicit, informed consent for a specific feature. Local-first is the default.
  * **Accessibility and Joy of Use**: The user interface must be clean, minimal, and intuitive. It must support both dark and light modes, include privacy features like blurring sensitive information for use in public spaces, and ensure all critical user flows are fully accessible via keyboard navigation. The application should be a pleasure to use.
  * **Automate the Tedious, Not the Personal**: The purpose of AI, OCR, and auto-categorization is to eliminate the friction of manual data entry, not to make decisions for the user. The application should learn from user behavior to become a smarter, more efficient assistant over time.

-----

### 2\. System Architecture & Service Responsibilities

The application is built on a **dockerized microservices pattern**, ensuring separation of concerns, scalability, and maintainability.

```
+----------------+      +------------------+      +----------------+
|   Frontend     | <--> |      Nginx       | <--> |   Backend API  |
| (React, Vite)  |      | (Reverse Proxy)  |      |   (FastAPI)    |
+----------------+      +------------------+      +-------+--------+
                                                          |
                                           +--------------+--------------+
                                           |              |              |
                                     +-----v-----+  +-----v----+   +-----v----+
                                     | PostgreSQL|  |   Redis  |   | ML Worker|
                                     |  (Data)   |  | (Cache/Q) |   | (Celery) |
                                     +-----------+  +----------+   +----------+
```

#### Docker Service Breakdown & Responsibilities:

  * **`nginx` (The Gatekeeper)**:

      * **Single Public Entrypoint**: All incoming traffic from the user's browser hits Nginx first.
      * **Request Routing**: It intelligently routes requests: UI assets are served by the `frontend` container, while API calls (`/api/...`) are forwarded to the `backend` container.
      * **Security**: Provides a critical security layer, handling SSL termination, rate limiting, and protecting the backend services from direct exposure.

  * **`frontend` (The User Experience)**:

      * **Responsibility**: Renders the entire user interface and manages all client-side state and interactions.
      * **Technology**: Built with React 18, TypeScript, and Vite for a modern, fast development experience.
      * **Real-time Sync**: Establishes a WebSocket connection with the backend for real-time data updates (e.g., new transactions appearing without a page refresh).
      * **Optimistic Updates**: Implements optimistic UI updates for a snappy user experience, where the UI updates immediately while the backend request is in flight.

  * **`backend` (The Brains)**:

      * **Responsibility**: Implements all business logic, manages data persistence, and orchestrates communication between other services. It exposes a REST and WebSocket API for the frontend.
      * **Technology**: A high-performance FastAPI application.
      * **Orchestration**: When a new transaction needs categorization, the backend doesn't do the ML work itself; it creates a task and places it on the Redis queue for the `ml-worker` to process.

  * **`postgres` (The Source of Truth)**:

      * **Responsibility**: The primary, persistent data store for all core financial and user data. This includes users, accounts, transactions, budgets, etc.
      * **Integrity**: Data integrity is enforced here through schemas, constraints, and transactions, managed by SQLAlchemy in the backend.

  * **`redis` (The Nervous System)**:

      * **Responsibility**: A multi-purpose, in-memory data store.
      * **Message Queue**: Acts as the message broker for Celery, allowing the `backend` to asynchronously delegate tasks to the `ml-worker`.
      * **Real-time Cache**: Caches session data or frequently accessed information to speed up API responses.
      * **Ephemeral Store**: Used for managing WebSocket connection states and other temporary data.

  * **`ml-worker` (The Specialist)**:

      * **Responsibility**: Handles all heavy computational AI/ML tasks, primarily transaction categorization. It listens for new tasks on the Redis queue, processes them, and returns the result.
      * **Isolation**: Running ML inference in a separate service prevents it from blocking or slowing down the main `backend` API.
      * **Technology**: Uses Sentence Transformers for semantic understanding and is optimized with ONNX for fast, CPU-based inference.

#### **CRITICAL: Single-Worker Architecture Constraint**

**The current application architecture requires running with exactly 1 Uvicorn worker process** (`UVICORN_WORKERS=1`) due to in-memory caching implementations in several services:

- **Automatic Sync Scheduler**: Uses TTLCache for sync job management  
- **Merchant Service**: Uses TTLCache for merchant recognition and user corrections
- **Auto Categorization Service**: Uses TTLCache for rule caching

**Why This Matters:**
- Multiple workers would have separate memory spaces, causing cache inconsistencies
- User corrections made on one worker wouldn't be available to others
- Sync job state could become fragmented across workers

**Current Solution:** 
- All caches use `cachetools.TTLCache` with bounded size and time-to-live
- Prevents memory leaks while maintaining single-worker compatibility
- Cache management methods available for monitoring and cleanup

**Future Enhancement Path:**
- Migrate to Redis-based distributed caching for multi-worker support
- Implement cache synchronization mechanisms
- Add worker health monitoring and failover capabilities

**Configuration:**
```bash
# Required for current architecture
UVICORN_WORKERS=1

# Cache settings (automatically applied)
SYNC_JOBS_CACHE_MAX_SIZE=500
MERCHANT_CACHE_MAX_SIZE=2000  
RULE_CACHE_MAX_SIZE=1000
```

-----

### 3\. Codebase Navigation & Architectural Patterns

Instead of memorizing specific filenames, understand the *purpose* of the directories.

#### Backend (`backend/app/`)

  * **`routes/`**: The API layer. Each file here defines a set of HTTP endpoints (e.g., `routes/transaction.py`). Its job is to handle incoming requests, validate the data using schemas, and call the appropriate service layer function. **Routes should not contain business logic.**
  * **`services/`**: The business logic layer. This is where the core application logic lives (e.g., `services/transaction_service.py`). Services orchestrate data operations, interact with other services (like the `ml_service`), and enforce business rules.
  * **`models/`**: The database object layer. Each file defines a database table using SQLAlchemy's declarative base (e.g., `models/transaction.py`). This is the single source of truth for the database structure.
  * **`schemas/`**: The data validation and serialization layer. These Pydantic models define the expected shape of API request and response bodies (e.g., `schemas/transaction.py`). They ensure data is clean before it enters the service layer and is formatted correctly before being sent to the client.
  * **`websocket/`**: Contains the logic for real-time communication, including the connection manager and definitions of WebSocket events.

#### Frontend (`frontend/src/`)

  * **`components/`**: Contains reusable UI components, organized by feature (e.g., `components/transactions/`).
  * **`services/`**: The frontend's data layer. These files are responsible for making API calls to the backend (e.g., `services/transactionService.ts`). They abstract away the details of HTTP requests.
  * **`stores/`**: The state management layer (using Zustand). These stores hold the application's state and provide methods for updating it.
  * **`hooks/`**: Contains custom React hooks that encapsulate reusable logic, such as fetching data (`useTransactions.ts`) or managing WebSocket connections (`useWebSocket.ts`).

-----

### 4\. Domain Data Model & Key Business Rules

  * **Core Objects**:
      * **User**: Represents an authenticated user of the system.
      * **Account**: A financial account (e.g., checking, savings, credit card) linked by a user.
      * **Transaction**: An individual financial event with a date, amount, description, and category.
      * **Category**: A user-defined category for transactions, which can be hierarchical (e.g., "Food" \> "Groceries").
      * **Budget**: A user-defined spending limit for a specific category over a time period.
      * **Goal**: A user-defined savings goal with a target amount and date.
  * **Crucial Business Rules**:
      * **Money is Always an Integer**: All monetary values are stored as **integer cents** in the database to avoid floating-point precision errors. All calculations are done with these integers. Convert to dollars/euros only at the final display stage in the frontend.
      * **Timestamps are Always UTC**: All dates and times are stored in the database in UTC. Conversion to the user's local timezone should only happen in the frontend.
      * **Auditability**: All significant user actions (creates, updates, deletes) must be auditable, linking the action back to a user and a timestamp.
      * **Soft Deletes vs. Hard Deletes**: Consider using soft deletes (marking records as deleted instead of removing them) for critical data like transactions to allow for "undo" functionality and maintain historical integrity.

-----

### 5\. AI Assistant Quick Reference & Guidelines

**Your Primary Directive**: Your mission is to assist in building, improving, and documenting this finance tracker. Every action you take and every line of code you write must align with the project's mission, architecture, and core philosophies outlined in this document.

**The File-First Approach**:

  * **Don't Reinvent the Wheel**: Before writing new code, always use this guide as a map to find the relevant files where similar functionality already exists. The project has a consistent structure; learn its patterns.
  * **Reference, Don't Memorize Code**: Do not store large code snippets in your memory. Instead, reference the actual, up-to-date files in the project. The codebase is the living source of truth.
  * **When in Doubt, Ask and Update**: If the user's request is ambiguous or requires a change to the architecture or business rules, first check the relevant files, then ask clarifying questions. Once a decision is made, update this memory document to reflect the change. This is living documentation.