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
