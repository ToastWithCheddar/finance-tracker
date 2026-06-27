"""Pytest config for ml-worker audit tests.

Provides:
  * sys.path shim so `from ml_classification_service import ...` works even
    though the ml-worker is not packaged as an installable module.
  * `minilm_model` session-scoped fixture loading the real MiniLM checkpoint
    once per test session.
  * `ML_AUDIT_SKIP_MODEL=1` env escape hatch for offline / CI-smoke runs.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ML_WORKER_DIR = REPO_ROOT / "ml-worker"
MODEL_DIR = REPO_ROOT / "ml_models" / "all-MiniLM-L6-v2"

# Make ml-worker source importable for future-wave tests.
if str(ML_WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(ML_WORKER_DIR))

# Match worker.py runtime knobs so model loading doesn't spawn extra threads.
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")


def _model_skip_reason() -> str | None:
    if os.environ.get("ML_AUDIT_SKIP_MODEL") == "1":
        return "ML_AUDIT_SKIP_MODEL=1 set; skipping model-dependent tests."
    if not MODEL_DIR.is_dir():
        return f"MiniLM checkpoint missing at {MODEL_DIR}."
    return None


@pytest.fixture(scope="session")
def model_dir() -> Path:
    reason = _model_skip_reason()
    if reason is not None:
        pytest.skip(reason)
    return MODEL_DIR


@pytest.fixture(scope="session")
def minilm_model(model_dir: Path):
    """Load `all-MiniLM-L6-v2` once per test session.

    Tests that just need embeddings should depend on this fixture; the load
    cost (~5-10s cold) is amortized over the whole session.
    """
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(str(model_dir), device="cpu")
