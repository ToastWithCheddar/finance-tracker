# Run Development

Option A: Docker compose (recommended)
- `./scripts/dev.sh`
- Frontend: http://localhost:3000
- Backend: http://localhost:8000 (docs at /docs)

Option B: Local only
- Backend: `uvicorn app.main:app --reload --port 8000` from `backend/`
- Frontend: `npm install && npm run dev` from `frontend/`

Seed data
- Backend auto-seeds default categories at startup.

