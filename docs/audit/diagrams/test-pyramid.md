# Test pyramid (post-W4 + IW-1)

Cited findings: BE-TEST-001..005, FE-TEST-001, ML-TEST-001.

```mermaid
flowchart TD
    subgraph e2e["E2E (slow, few)"]
        E1["Playwright @ e2e/<br/>~18 specs<br/>auth, dashboard, transactions, accessibility"]
    end
    subgraph integration["Integration (testcontainers)"]
        I1["backend/tests/integration/<br/>real Postgres + Redis<br/>HTTP via httpx ASGITransport"]
        I2["ml-worker/tests/integration/<br/>Celery in-process"]
    end
    subgraph unit["Unit"]
        U1["backend/tests/{unit,security,concurrency,contract}/<br/>pytest, hypothesis, respx"]
        U2["frontend/tests/{services,hooks,stores,components,utils}/<br/>Vitest + RTL + MSW + happy-dom<br/>~70 specs"]
        U3["ml-worker/tests/unit/<br/>~52 specs (LRU, confidence, prototype I/O)"]
    end

    e2e --> integration --> unit
```

## Tooling per tier

| Tier | Backend | Frontend | ML-worker |
|---|---|---|---|
| Unit | pytest, hypothesis, respx, freezegun | Vitest, RTL, MSW, happy-dom | pytest, numpy fixtures |
| Integration | testcontainers (Postgres + Redis), httpx ASGITransport | Vitest with MSW network mocks | Celery test app |
| E2E | — | Playwright + axe-playwright + axe-core | — |
| Bench | Locust, pytest-benchmark | Lighthouse CI 0.14, bundle-visualizer | pytest-benchmark for inference |

## CI flow

```mermaid
sequenceDiagram
    participant Dev as Developer push
    participant GH as GitHub Actions<br/>.github/workflows/ci.yml
    participant TC as testcontainers
    participant LH as Lighthouse CI

    Dev->>GH: push / PR
    GH->>GH: lint (ruff + npm lint)
    GH->>TC: backend integration tests
    GH->>GH: vitest:run (frontend)
    GH->>GH: ml-worker pytest
    GH->>LH: bench-frontend-build-check (assertions only)
    Note over GH: e2e suite triggered<br/>by manual workflow dispatch<br/>(needs live stack)
```

## Concurrency group

`name: ci` with `concurrency: ${{ github.ref }}` cancels prior runs on new
pushes — saves CI minutes.
