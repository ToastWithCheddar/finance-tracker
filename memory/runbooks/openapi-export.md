# Export OpenAPI (FastAPI)

Goal: Keep `memory/contracts/backend_openapi.json` in sync with the running backend.

Steps
- Start backend locally:
  - Docker: `docker-compose up backend`
  - Or local: from `backend/` run `uvicorn app.main:app --reload --port 8000`
- Export the spec:
  - `curl -s http://localhost:8000/openapi.json > memory/contracts/backend_openapi.json`
- Regenerate frontend types:
  - `chmod +x scripts/types-from-openapi.sh && ./scripts/types-from-openapi.sh`
- Validate:
  - Ensure generated files changed only when you intended to update contracts.
- Commit:
  - Include both the updated `backend_openapi.json` and any changes under `frontend/src/api/generated/`.
