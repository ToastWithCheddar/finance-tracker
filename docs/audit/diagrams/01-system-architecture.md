# Şekil 1 — Sistem Mimarisi (Yüksek Seviye)

Tarayıcıdan başlayarak veri ve kontrol akışı: nginx (TLS 443 + HSTS) →
React SPA + FastAPI; Postgres / Redis / ml-worker iç ağda; Supabase ve
Plaid dış servisler. WebSocket lane gerçek zamanlı güncellemeleri,
Celery lane ML işlerini taşır.

```mermaid
flowchart LR
    Browser((Tarayıcı))

    subgraph edge["Edge"]
      Nginx["nginx<br/>:443 TLS + HSTS"]
    end

    subgraph app["Uygulama Katmanı"]
      FE["frontend<br/>React 18 + Vite<br/>(statik, nginx servisi)"]
      API["backend<br/>FastAPI + uvicorn<br/>structlog · Prometheus"]
    end

    subgraph data["Veri & İş Kuyruğu"]
      PG[(Postgres 15<br/>RLS · alembic)]
      R[(Redis 7<br/>cache · pubsub · CAS-DEL lock)]
      ML["ml-worker<br/>Celery · ONNX-INT8 MiniLM<br/>OrderedDict LRU"]
    end

    subgraph ext["Dış Servisler"]
      SB[("Supabase Auth<br/>JWT + Webhook")]
      PL[("Plaid Sandbox<br/>OAuth + Transactions")]
    end

    Browser -- HTTPS --> Nginx
    Nginx -- "/" --> FE
    Nginx -- "/api/*" --> API
    Nginx -. "WS /ws/* (auth in first frame)" .-> API
    API -. "broadcast" .-> Browser

    API --> PG
    API --> R
    API -- "task enqueue" --> R
    R -- "task dequeue" --> ML
    ML --> PG
    ML --> R

    API <-- "JWT verify / webhook" --> SB
    API <-- "OAuth Link / sync" --> PL
```

## Kanıt ve Çapraz Referanslar

- nginx + 443 + HSTS: `nginx/nginx.conf`, `docs/integration/12-operator-items.md`.
- Backend ile uçtan uca güvenlik kontrolleri: `docs/audit/diagrams/security-topology.md`.
- Konteyner topolojisi (volume / network ayrımı): `docs/audit/diagrams/prod-compose.md`.
- Gözlemlenebilirlik kanalları (OTel → Grafana): `docs/audit/diagrams/observability-flow.md`.
