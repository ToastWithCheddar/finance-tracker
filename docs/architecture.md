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
    Backend -->|HTTP ML Requests| MLWorker[ML Worker (HTTP API)]

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
*   **Service Communication**: Heavy or long-running tasks (e.g., ML model training, batch processing) are handled by a dedicated ML Worker via HTTP API calls, ensuring the main API remains responsive and maintains clear service boundaries.
*   **Containerization**: Docker and Docker Compose are used to package each service into isolated containers, providing consistent environments across development, testing, and production.
*   **Layered Architecture**: Each service (especially the backend) follows a layered design (e.g., API routes, business logic services, data access layer) to separate concerns.
*   **Real-time Capabilities**: Redis-based pub/sub WebSocket system enables scalable real-time updates to the frontend, providing an interactive and dynamic user experience with message persistence.
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
*   **ML Service Integration**: Communicates with the ML Worker via HTTP-based MLServiceClient for transaction categorization and model management.
*   **WebSockets**: Manages scalable Redis-based WebSocket connections for real-time data push to the frontend with message persistence and multi-instance support.

### 3.3. ML Worker (HTTP API/Python)

*   **Purpose**: A dedicated service for performing computationally intensive machine learning tasks via HTTP API.
*   **Technology Stack**: Python, FastAPI/Flask (HTTP server), Sentence Transformers, ONNX Runtime.
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
*   **Scalability**: The microservices architecture allows individual services to be scaled independently based on demand. HTTP-based ML service communication provides clear service boundaries and horizontal scaling capabilities.
*   **Maintainability**: Clear separation of concerns, modular codebase, and strong typing (TypeScript, Python type hints) contribute to easier maintenance and development.
*   **Observability**: Logging, monitoring (Prometheus), and A/B testing provide insights into system health and performance.

This comprehensive architecture provides a robust, scalable, and maintainable foundation for the finance tracker application, designed to handle complex financial data processing and deliver a rich user experience.