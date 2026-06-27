# ml-worker test scaffolding (foundation wave)

Net-new tests for `ml-worker/`. The internship code under `ml-worker/` is **not modified** by this scaffolding; helpers under `helpers/` document the shape of forthcoming production changes (Section F).

## Layout

```
ml-worker/tests/
├── pyproject.toml          pinned deps
├── conftest.py             session-scoped MiniLM fixture; sys.path shim for ml-worker imports
├── unit/
│   ├── test_prototype_math.py     mean-of-embeddings + cosine sim invariants
│   ├── test_lru_cache_proposal.py target LRU semantics for the future cache
│   └── test_confidence_buckets.py >=0.75 high, >=0.55 medium, else low (per F-ml-worker-revival.md)
└── helpers/
    └── confidence.py       proposed `bucket(sim) -> str` to be moved into ml-worker source by Section F
```

## What is intentionally **not** covered here

- Celery / Redis end-to-end tests — deferred to a later wave.
- PyTorch vs ONNX parity — deferred to Section F (ONNX path is not wired in yet).
- Backend-side classification integration — covered under `backend/tests/`.

## Run

```bash
cd ml-worker/tests
python -m venv .venv
.venv/bin/pip install -e .
.venv/bin/pytest -x -v
```

The session-scoped fixture loads `ml_models/all-MiniLM-L6-v2/` (~90 MB MiniLM safetensors) **once per session**. First-run cold load is ~5–10s on a fast machine; subsequent tests reuse the cached encoder. Total runtime target: < 30 s.

If model load is undesired (CI smoke, offline boxes), set `ML_AUDIT_SKIP_MODEL=1` to skip the embedding-dependent tests; the LRU and confidence-bucket tests still run.
