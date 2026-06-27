# Section F — ML-Worker Revival

**Owner agent:** Opus 4.7, **high effort** (debugging-heavy: model parity, async orchestration, ONNX runtime quirks).

## Scope

User decision: **revive** the dead optimization stack rather than delete it. Findings: ML-PR-001..005, ML-PERF-001, ML-LOG-001, ML-TEST-001, ML-SEC-001 (handoff to Section E).

## Goal

Make the optimized inference path the **live** path:
- `ProductionOrchestrator` instantiated and initialized in `worker_ready`.
- `OptimizedInferenceEngine` serves `classify_transaction` requests with ONNX-INT8 + LRU embedding cache.
- `ModelMonitoring` exposes `/metrics` on **port 8002** (avoiding the backend port 8000 collision).
- PyTorch sentence-transformers retained as a fallback.

## Tasks

### 1. Wire the orchestrator (ML-PR-001)

`ml-worker/worker.py`:
- Remove the `_is_light_startup` short-circuit, or gate it on an env var `ML_LIGHT_STARTUP=true` defaulting to false.
- In `worker_ready`:
  ```python
  global production_orchestrator
  production_orchestrator = await create_production_orchestrator(
      model_name="all-MiniLM-L6-v2",
      models_dir=os.getenv("MODELS_DIR", "/app/models"),
      enable_ab_testing=settings_get("ENABLE_AB_TESTING", False),
      prometheus_port=int(os.getenv("ML_METRICS_PORT", "8002")),
  )
  await production_orchestrator.initialize_production()
  ```

### 2. Live ONNX path (ML-PERF-001)

In `production_orchestrator.classify_transaction` (verify in `ml-worker/production_orchestrator.py`):
- Default to `OptimizedInferenceEngine` ONNX session.
- Health check on init: run a sample inference; on failure, fall back to PyTorch and log a structured `level=error event="onnx-init-failed"`.

### 3. Embedding cache → real LRU (ML-PR-004)

In `optimized_inference_engine.py:188-210`, replace the FIFO eviction with `collections.OrderedDict.move_to_end` on hit, or use `cachetools.LRUCache(maxsize=10000)`.

### 4. Worker-shared event loop (ML-PR-003)

In `worker.py`:
- Allocate one `loop = asyncio.new_event_loop()` at module import.
- Tasks call `asyncio.run_coroutine_threadsafe(coro, loop).result()` (Celery prefork is single-threaded per child, so a per-worker loop running in a dedicated thread is fine).
- Document the trade-off in `docs/runbooks/ml-worker-async-model.md`.

### 5. Real confidence (ML-PR-002)

`ml_classification_service.py:984, 1043`:
- Compute `confidence_level` from the cosine similarity:
  - `>= 0.75` → "high"
  - `>= 0.55` → "medium"
  - else → "low"
- Wire the threshold logic in monitoring & in backend `TransactionService.create_transaction` (already gated on `ML_CONFIDENCE_THRESHOLD`).

### 6. Pickle removal (ML-SEC-001 — handed to Section E execution but defined here)

`ml_classification_service.py:1141-1148`: replace `pickle` with `numpy.save` + JSON sidecar.

### 7. Logging (ML-LOG-001)

Replace three `logging.basicConfig` calls with a single `backend/app/core/logging_config.py` import. Strip emoji from log messages.

### 8. Model weight handling (ML-PR-005, also Section D)

`ml-worker/scripts/fetch_models.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail
mkdir -p "${MODELS_DIR}"
aws s3 sync "s3://${MODELS_BUCKET}/all-MiniLM-L6-v2/" "${MODELS_DIR}/all-MiniLM-L6-v2/" --no-progress
[[ -f "${MODELS_DIR}/category_prototypes.npy" ]] || python -m ml_worker.scripts.build_prototypes
```
Run in entrypoint before starting Celery.

## Tests (`ml-worker/tests/`)

```
ml-worker/
├── pyproject.toml
├── conftest.py                 # pytest-celery eager + Redis container; loads model from fixture path
├── fixtures/
│   ├── golden_set.csv          # 200 hand-labeled transactions
│   └── tiny_model/             # 1MB stub model for speed
├── unit/
│   ├── test_prototype_math.py  # mean-of-embeddings invariants
│   ├── test_lru_cache.py       # MRU promotion, eviction order
│   └── test_confidence_buckets.py
├── parity/
│   └── test_pytorch_vs_onnx.py # cosine sim >= 0.999 on golden set
├── celery/
│   ├── test_classify_task.py
│   ├── test_batch_classify_task.py
│   └── test_add_example_task.py
└── monitoring/
    └── test_metrics_endpoint.py # asserts /metrics on :8002 returns Prometheus format
```

## Benchmarks (`benchmarks/ml-worker/`)

`bench.py`:
- Measure cold-start time (process start → first inference).
- p50/p95/p99 single-inference latency at concurrency 1, 2, 4, 8.
- Memory RSS over time.
- Throughput (transactions/sec) for batched inference (batch sizes 1, 8, 32, 128).
- Cache hit rate over a 10k-transaction synthetic stream.
- Compare PyTorch baseline vs ONNX-INT8.
- Output `benchmarks/ml-worker/<git-sha>/report.json` + a markdown summary.

Target after revival:
- p99 single-inference < 50 ms (current ~150-300 ms in PyTorch path).
- Cache hit rate ≥ 30% on realistic streams.
- Memory ≤ 600 MB per worker child.

## Deliverables

- Internship-code edits in `ml-worker/{worker,production_orchestrator,optimized_inference_engine,ml_classification_service,model_monitoring}.py`.
- `ml-worker/scripts/fetch_models.sh`, `ml-worker/scripts/build_prototypes.py`.
- Tests under `ml-worker/tests/`.
- Benchmarks under `benchmarks/ml-worker/`.
- `docs/runbooks/ml-worker-async-model.md`, `docs/runbooks/ml-worker-rollback.md`.

## Success metrics

- `production_orchestrator` is non-None at runtime.
- `curl http://ml-worker:8002/metrics` returns Prometheus exposition format.
- Parity test passes on golden set.
- p99 latency target met in benchmark.
- ml-worker container starts in < 30 s and answers a Celery task within 5 s of ready signal.

## Agent prompt template

> Finance-tracker ML-worker revival. Opus 4.7 **high effort** thinking. Read `docs/audit/snapshot/ml-worker-map.md` and `docs/audit/improvement-sections/F-ml-worker-revival.md`. Wire the orchestrator, switch the live path to ONNX-INT8, fix the cache and event loop, expose metrics. Keep PyTorch as a fallback. Author tests + benchmarks under `ml-worker/tests/` and `benchmarks/ml-worker/`. Run the benchmark; if a metric regresses vs PyTorch baseline, debug before declaring done. Update findings.csv.
