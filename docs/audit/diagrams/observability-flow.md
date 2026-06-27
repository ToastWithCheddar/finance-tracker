# Observability flow (post-W5)

Cited findings: BE-LOG-001..004, FE-LOG-001..002, ML-LOG-001, INFRA-OBS-001..002.

```mermaid
flowchart LR
    subgraph apps["Application processes"]
        BE["FastAPI<br/>backend/app/logging_config.py<br/>(structlog JSON)"]
        ML["ml-worker (Celery)<br/>ml-worker/app/logging_config.py"]
        FE["React app<br/>frontend/src/utils/logger.ts<br/>(level-gated)"]
    end

    subgraph collect["Collection"]
        OTEL["OpenTelemetry Collector<br/>ops/observability/otel/collector-config.yaml"]
        PROM["Prometheus<br/>(via prometheus-fastapi-instrumentator)"]
    end

    subgraph store["Storage / UI"]
        LOKI["Loki"]
        TEMPO["Tempo (traces)"]
        GRAFANA["Grafana<br/>ops/observability/grafana/dashboards/"]
        SENTRY["Sentry SaaS<br/>(error events only)"]
    end

    BE -- "stdout JSON" --> OTEL
    ML -- "stdout JSON" --> OTEL
    FE -- "fetch /api/log<br/>(production only)" --> BE
    BE -- "/metrics" --> PROM
    ML -- "ML_METRICS_PORT (8002)" --> PROM
    OTEL --> LOKI
    OTEL --> TEMPO
    PROM --> GRAFANA
    LOKI --> GRAFANA
    TEMPO --> GRAFANA
    BE -. "uncaught exceptions" .-> SENTRY
    FE -. "ErrorBoundary" .-> SENTRY
```

## Compose wiring

`docker-compose.observability.yml` (repo root) brings up the OTel collector,
Prometheus, Loki, Tempo, and Grafana with mounts at `./ops/observability/...`.
`docker compose -f docker-compose.observability.yml config -q` is part of IW-7
verification.

## Health / liveness

```mermaid
flowchart TD
    K[Kubernetes / Compose<br/>liveness probe] --> L["GET :8003/live<br/>(always 200)"]
    K2[readiness probe] --> R["GET :8003/ready<br/>polls ProductionOrchestrator.health()"]
    L -.-> HP[ml-worker/scripts/health_probe.py]
    R -.-> HP
```
