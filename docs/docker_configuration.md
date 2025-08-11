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
