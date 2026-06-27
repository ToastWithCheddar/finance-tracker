# Section C — Logging & Observability

**Owner agent:** Opus 4.7, medium effort. Single agent.

## Scope

Findings: BE-LOG-001..004, BE-WS-002, FE-LOG-001..002, FE-SEC-004, FE-PR-002, ML-LOG-001, INFRA-OBS-001..002.

## Pillars

1. **Structured logs** (JSON, correlation IDs) end-to-end.
2. **Metrics** (Prometheus-compatible) on every long-running service.
3. **Tracing** (OpenTelemetry) across HTTP → DB → Redis → Celery.
4. **Error reporting** (Sentry/GlitchTip) on frontend.

## Backend

### Structlog

Replace `logging.basicConfig` (`backend/app/main.py:33-40`) with structlog:

```python
# backend/app/core/logging_config.py
import structlog, logging
def configure_logging(level: str = "INFO", json_output: bool = True):
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    processors.append(
        structlog.processors.JSONRenderer() if json_output
        else structlog.dev.ConsoleRenderer(colors=True)
    )
    structlog.configure(processors=processors, wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level)))
```

Wire from `app/main.py` startup. Replace `logger = logging.getLogger(__name__)` with `logger = structlog.get_logger(__name__)` everywhere (codemod with ruff or simple sed).

### Request ID propagation

Fix BE-LOG-001:
- Generate `request_id` early in middleware, set on `request.state.request_id`.
- Bind via `structlog.contextvars.bind_contextvars(request_id=request_id, user_id=...)` at start of each request.
- Echo back as `X-Request-ID` response header.
- Pass to Celery via `apply_async(headers={"X-Request-ID": request_id})`.
- ml-worker reads from `task.request.headers` and binds.

### Metrics

Add `prometheus-fastapi-instrumentator` (already MIT-licensed, ~250 LOC dep):
```python
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app, endpoint="/metrics")
```
Custom metrics:
- `transactions_created_total{user_id_bucket}` — counter.
- `ml_categorize_latency_seconds` — histogram.
- `ws_active_connections` — gauge.

### Tracing

`opentelemetry-instrumentation-fastapi` + `opentelemetry-instrumentation-sqlalchemy` + `opentelemetry-instrumentation-redis` + `opentelemetry-instrumentation-celery`. OTLP exporter to a configurable collector URL. Default: disabled in dev.

### SQL log redaction

BE-LOG-003: in `database.py:106-110`, truncate parameter lists to 100 chars and apply a redact-known-PII filter (`email`, `password`, `token` keys).

## Frontend

### Strip console.*

Add ESLint rule:
```js
{ "no-console": ["error", { "allow": ["warn", "error"] }] }
```
Replace transient debug logs with structured logger:
```ts
// frontend/src/lib/logger.ts
export const log = {
  debug: (msg: string, ctx?: object) => import.meta.env.DEV && console.debug(msg, ctx),
  info: (msg: string, ctx?: object) => Sentry.addBreadcrumb({ message: msg, data: ctx, level: 'info' }),
  warn: ...,
  error: (msg: string, err?: unknown, ctx?: object) => { Sentry.captureException(err ?? new Error(msg), { contexts: { custom: ctx } }); }
};
```

### Sentry / GlitchTip

Init in `main.tsx`:
- DSN from `VITE_SENTRY_DSN`.
- `tracesSampleRate: 0.1` in prod.
- `replaysOnErrorSampleRate: 1.0`.
- Per-route `<ErrorBoundary>` (FE-PR-002): wrap each route element, fall back to `ErrorState` UI.

### Toast consolidation

FE-LOG-002: keep `sonner`, remove `react-hot-toast` from `package.json`. Codemod imports.

### Token logging

FE-SEC-004: remove `api.ts:77,79` `console.log(...)` calls.

## ml-worker

Single structlog config (replacing three `logging.basicConfig` calls in `worker.py`, `ml_classification_service.py`, `optimized_inference_engine.py`). Strip emoji from log messages (some shippers choke on multi-byte chars).

Restart Prometheus monitoring: handled in Section F.

## Infrastructure

- **Log aggregation:** add Loki + Promtail sidecar in `docker-compose.test.yml` and `docker-compose.prod.yml`. Document deploy options in `docs/runbooks/observability-stack.md`.
- **Metrics scrape:** Prometheus container with scrape configs for backend `/metrics` and ml-worker `:8002/metrics`.
- **Tracing collector:** optional Jaeger or Tempo container.
- **Dashboards:** seed Grafana with two dashboards under `ops/observability/grafana/` (HTTP latency, ML latency).

## Deliverables

- `backend/app/core/logging_config.py`
- `frontend/src/lib/logger.ts`
- `ops/observability/grafana/dashboards/*.json`
- `ops/observability/otel/collector-config.yaml`
- `docker-compose.observability.yml`
- `docs/runbooks/observability-stack.md`
- Internship-code edits to `app/main.py`, `app/database.py`, `frontend/src/main.tsx`, `frontend/src/services/api.ts`, ml-worker module heads.

## Success metrics

- Single JSON log line per request, includes `request_id`, `user_id`, `path`, `method`, `status`, `latency_ms`.
- Same `request_id` visible in backend log AND ml-worker log for the same Celery task.
- `/metrics` returns valid Prometheus format on backend (and ml-worker after F lands).
- Frontend captures unhandled errors in Sentry with breadcrumbs.
- Zero `console.*` (other than `warn`/`error`) in `frontend/src/`.

## Agent prompt template

> Finance-tracker observability work. Opus 4.7, medium effort. Read `docs/audit/improvement-sections/C-logging-observability.md`. Author the deliverables listed; modify internship code only at the integration points called out. Validate by running `make audit-test-all` and `docker compose -f docker-compose.observability.yml up`, then issuing 10 sample requests and confirming logs/metrics/traces. Update findings.csv.
