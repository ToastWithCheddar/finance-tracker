# Observability Stack — Runbook

Structured logs, Prometheus metrics, OpenTelemetry collector wiring, Grafana
dashboards, and the frontend Sentry + prod-safe logger.

## Layout

```
backend/app/logging_config.py          # Backend structlog config
ml-worker/app/logging_config.py        # ml-worker structlog config (mirror of backend)
frontend/src/utils/logger.ts           # Frontend logger (Sentry + prod-safe console replacement)
ops/observability/
├── otel/collector-config.yaml         # OTLP receiver -> Prometheus + logging exporters
└── grafana/dashboards/
    └── backend-overview.json          # HTTP rps, p95 latency, 5xx, pg pool
```

Both `backend/app/logging_config.py` and `ml-worker/app/logging_config.py` are
canonical-by-design. They are kept in sync manually because each service owns
its own dependency tree; if you change one, mirror the change to the other.

## Environment variables

| Var                | Default        | Purpose                                                     |
| ------------------ | -------------- | ----------------------------------------------------------- |
| `ENVIRONMENT`      | `development`  | Anything other than `development` switches to JSON renderer |
| `LOG_LEVEL`        | `INFO`         | Standard Python log level name                              |
| `LOG_SQL_PARAMS`   | unset (false)  | Enable SQLAlchemy parameter logging — dev-only, truncated   |
| `METRICS_ENABLED`  | `true`         | Mounts `/metrics` via `prometheus-fastapi-instrumentator`   |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | unset | Pointed at the collector for traces                     |
| `VITE_SENTRY_DSN`  | unset          | When set, enables Sentry init in `frontend/src/main.tsx`    |

## Ports

- Backend `/metrics`: same port as the API (default 8000)
- ml-worker `/metrics`: 8002
- OTel collector OTLP gRPC: 4317
- OTel collector OTLP HTTP: 4318
- OTel collector Prometheus exporter: 8889
- OTel collector health: 13133

## How to add a new metric

Backend (FastAPI):

```python
from prometheus_client import Counter
TRANSACTIONS_CREATED = Counter(
    "transactions_created_total",
    "Number of transactions created",
    ["user_id_bucket"],
)
TRANSACTIONS_CREATED.labels(user_id_bucket="paid").inc()
```

The metric is automatically scraped by Prometheus through
`prometheus-fastapi-instrumentator`'s `/metrics` endpoint, which is mounted in
`backend/app/main.py` at startup (gated by `settings.METRICS_ENABLED`).

## Frontend logger

`frontend/src/utils/logger.ts` replaces `console.*` across the app, strips
sensitive headers / fields before emitting, and routes through Sentry in prod
when `VITE_SENTRY_DSN` is set.
