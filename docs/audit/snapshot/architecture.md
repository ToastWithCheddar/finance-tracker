# Architecture snapshot

Snapshot of `finance-tracker` as of the audit start. Frozen for reference; not maintained as code evolves.

## Services

| Service | Tech | Port (container) | Port (host) | Purpose |
|---|---|---|---|---|
| `postgres` | postgres:15-alpine | 5432 | 5432 | Primary store |
| `redis` | redis:7-alpine | 6379 | 6379 | Cache, pub/sub, Celery broker, distributed locks |
| `backend` | FastAPI 0.104+, Python 3.11, SQLAlchemy 2.0, psycopg2 (sync) | 8000 | 8000 | REST + WebSocket + Plaid/Supabase webhooks |
| `frontend` | React 19.1, TypeScript 5.8, Vite 7 | 3000 (dev) / 80 (prod target — broken) | 3000 (dev) | SPA |
| `ml-worker` | Celery 5, Python 3.11, sentence-transformers, ONNX runtime | n/a (no HTTP) | 8001 mapped but unused | Async transaction categorization |
| `nginx` | nginx:alpine | 80, 443 | 80, 443 | Reverse proxy, rate-limit, WS upgrade |

`docker-compose.yml` is dev-mode despite naming (volume-mounted code, `--reload`, `target: dev` for frontend). `docker-compose.dev.yml` is a near-noop overlay. **There is no production compose.**

## Data flow (HTTP path)

```
Browser ──https──> nginx ──http──> backend (FastAPI)
                          │
                          ├──> Postgres (sync psycopg2 over SQLAlchemy)
                          ├──> Redis (cache, pub/sub fanout)
                          ├──> Supabase Auth (JWT verify, register/login)
                          ├──> Plaid API (link, exchange, sync)
                          └──> Celery (Redis broker) ──> ml-worker
                                                              │
                                                              └──> sentence-transformers MiniLM
                                                                   (PyTorch path; ONNX-INT8 generated but unused)
```

## Data flow (WebSocket path)

```
Browser ──wss──> nginx /ws ──ws──> backend (FastAPI WS)
                                        │
                                        ├──> per-user Redis subscriber task
                                        │       (channel: ws:user:{user_id})
                                        ├──> initial full_sync push (financial_health snapshot)
                                        └──> 30-min idle cleanup task
```

Cross-instance fanout: any backend pod publishes to `ws:user:{user_id}`; subscribers on whichever pod holds that user's socket forward to the WebSocket.

## External dependencies

- **Supabase** — auth (JWT, email/password, password reset, MFA), webhooks for `user.updated`, `user.deleted`.
- **Plaid** — sandbox creds in `.env.example`. Link → exchange → access_token (Fernet-encrypted at rest) → sync transactions / balances. Webhooks for sync events.
- **`sentence-transformers/all-MiniLM-L6-v2`** — 90 MB, CPU. Few-shot prototypes via cosine similarity.

## Repo layout (top level)

```
finance-tracker/
├── backend/             # FastAPI + SQLAlchemy + Alembic + Celery client
├── frontend/            # React + Vite + Zustand + TanStack Query
├── ml-worker/           # Celery worker + ML stack
├── ml_models/           # 250 MB of model weights (committed!)
├── nginx/               # nginx.conf, empty ssl/
├── scripts/             # 3 small shell scripts (dev, prod, check)
├── docker-compose.yml   # dev-mode despite name
├── docker-compose.dev.yml
├── ci.yml               # 0 bytes (empty file)
├── repomix-output.xml
├── DiagramModel.drawio.svg
└── audit/               # ← post-internship work
```

## Migration & seeding

- Single Alembic revision `0ebba5935295_initial_schema.py`. After this, all schema evolution is via `Base.metadata.create_all` at startup (`backend/app/main.py:66`). **Schema drift is unmanaged.**
- Default categories seeded on every startup (idempotent by count, but TOCTOU-prone with multiple workers).
