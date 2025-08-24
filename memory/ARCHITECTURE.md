
# Architecture

## Data Flow

1.  **Frontend (React)**:
    *   UI components in `frontend/src/components` render the application.
    *   `frontend/src/App.tsx` is the main entry point, managing routing and auth state.
    *   Services in `frontend/src/services` (e.g., `transactionService`, `accountService`, `authService`) are responsible for making API calls.
    *   A central `apiClient` in `frontend/src/services/api.ts` handles all HTTP requests, including adding auth tokens and silent refresh.
    *   The `VITE_API_URL` environment variable configures the backend URL.

2.  **Backend (FastAPI)**:
    *   The FastAPI application is defined in `backend/app/main.py`.
    *   It includes routers from `backend/app/routes` for different resources (e.g., `/accounts`, `/transactions`, `/auth`).
    *   Services in `backend/app/services` contain the business logic.
    *   Models are defined in `backend/app/models` and schemas in `backend/app/schemas`.
    *   Authentication is handled via JWTs, with Supabase as a potential provider.

3.  **Database (PostgreSQL)**:
    *   The backend uses SQLAlchemy to interact with a PostgreSQL database.
    *   Alembic is used for database migrations.

4.  **ML Worker (Python)**:
    *   A separate worker process for machine learning tasks (e.g., transaction categorization).
    *   Communicates with the backend, likely via a message queue or direct API calls.
