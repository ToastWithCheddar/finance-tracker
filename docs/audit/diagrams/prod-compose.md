# Production compose topology (post-W6)

Cited findings: INFRA-DOCK-001..005, INFRA-NGINX-001..002, BE-PR-001..006,
FE-PR-001..005, ML-PR-001..005.

```mermaid
flowchart LR
    Internet((Internet))
    subgraph host["Host / VM"]
        N["nginx<br/>:443 + HSTS<br/>multi-stage build"]
        FE["frontend (static)<br/>nginx :8080 internal<br/>multi-stage build"]
        API["backend (FastAPI)<br/>uvicorn workers<br/>prod / prod-no-models target"]
        ML["ml-worker (Celery)<br/>worker_init event loop<br/>:8002 metrics, :8003 health"]
        PG[(postgres<br/>+ alembic)]
        R[(redis<br/>maxmemory + LRU)]
        OBS["observability stack<br/>(separate compose)"]
    end

    Internet -- "TLS" --> N
    N -- "/api → :8000" --> API
    N -- "/ → :8080" --> FE
    API --> PG
    API --> R
    API --> ML
    ML --> R
    ML --> PG
    API -. "metrics" .-> OBS
    ML -. "metrics" .-> OBS
```

## Image layout

Both backend and ml-worker Dockerfiles ship two prod targets:
- `prod`: bakes the ONNX-INT8 model + safetensors prototypes into the image.
- `prod-no-models`: leaves models out; `ml-worker/scripts/fetch_models.sh`
  pulls them from object storage at container start. Lets the same image
  run in environments with different model SLAs.

## Operator follow-ups (deferred)

These are intentionally **not** wired in compose; they require infra the
team owns:

| Item | Where | Status |
|---|---|---|
| Real TLS certs | `nginx/ssl/` | INFRA-NGINX-001 deferred — operator |
| Backup S3 bucket | `make backup` cron | INFRA-BACKUP-001 deferred — operator |
| `git filter-repo` for ml_models history | repo root | ML-PR-005 deferred — operator |
| react-window install | `frontend/package.json` | FE-PERF-003 deferred — operator (`npm install`) |
| Alembic catchup baseline migration | `backend/migrations/` | BE-PR-001/002 deferred — operator (needs fresh DB) |
