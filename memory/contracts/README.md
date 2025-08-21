# Contracts

- `backend_openapi.json`: Authoritative backend API spec exported from the running FastAPI app.
- `events.md`: Domain events and payload schemas (if any).
- `models.md`: Cross-cutting types/enums shared by multiple endpoints.

How to update backend_openapi.json (development):
1) Start backend locally (e.g., `docker-compose up backend` or `poetry run uvicorn app.main:app --reload`).
2) Visit `http://localhost:8000/openapi.json`.
3) Save response to `memory/contracts/backend_openapi.json`.
4) Run `./scripts/types-from-openapi.sh` to regenerate FE client/types.
5) Commit both the spec and generated diff (should be clean after regeneration).

Note: This repo uses contract-first integration: update the spec first, then regenerate, then code.
