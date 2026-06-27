"""Section F (ML-PR-004): assert the real LRU now lives inside
`optimized_inference_engine.OptimizedInferenceEngine.embedding_cache` —
backed by `collections.OrderedDict` with move-to-end on hit and
popitem(last=False) on overflow.

These tests exercise the cache *directly* via the engine's
`_get_embedding_cached` method but stub out `sentence_model.encode` to
avoid loading the real MiniLM checkpoint. That keeps the tests offline-safe
under `ML_AUDIT_SKIP_MODEL=1`.
"""

from __future__ import annotations

from collections import OrderedDict
from unittest.mock import MagicMock

import numpy as np
import pytest


def _make_engine(maxsize: int = 3):
    # Import inside the test to honor conftest sys.path shim.
    from optimized_inference_engine import OptimizedInferenceEngine

    eng = OptimizedInferenceEngine.__new__(OptimizedInferenceEngine)
    # Skip __init__ to avoid CPU-affinity/thread tweaks.
    eng.embedding_cache = OrderedDict()
    eng.cache_max_size = maxsize
    eng.inference_stats = {
        'total_inferences': 0,
        'total_time_ms': 0,
        'avg_time_ms': 0,
        'max_time_ms': 0,
        'min_time_ms': float('inf'),
        'cache_hits': 0,
        'cache_misses': 0,
    }
    import threading
    eng.lock = threading.RLock()

    # Each unique text returns a unique vector so we can verify lookup.
    counter = {"n": 0}

    def fake_encode(texts, convert_to_tensor=False, **_):
        counter["n"] += 1
        return [np.array([counter["n"]], dtype=np.float32)]

    eng.sentence_model = MagicMock()
    eng.sentence_model.encode.side_effect = fake_encode
    return eng


def test_cache_is_ordereddict_for_real_lru():
    eng = _make_engine()
    assert isinstance(eng.embedding_cache, OrderedDict)


def test_hit_promotes_to_mru():
    eng = _make_engine(maxsize=3)
    eng._get_embedding_cached("a")
    eng._get_embedding_cached("b")
    eng._get_embedding_cached("c")
    keys_before = list(eng.embedding_cache.keys())
    assert keys_before == [hash("a"), hash("b"), hash("c")]

    eng._get_embedding_cached("a")  # hit — should move 'a' to end
    keys_after = list(eng.embedding_cache.keys())
    assert keys_after[-1] == hash("a")
    assert eng.inference_stats['cache_hits'] == 1


def test_miss_evicts_least_recently_used():
    eng = _make_engine(maxsize=2)
    eng._get_embedding_cached("a")
    eng._get_embedding_cached("b")
    eng._get_embedding_cached("a")  # 'a' becomes MRU; 'b' is LRU
    eng._get_embedding_cached("c")  # evicts 'b'
    keys = list(eng.embedding_cache.keys())
    assert hash("b") not in keys
    assert hash("a") in keys
    assert hash("c") in keys


def test_repeated_inserts_do_not_grow_beyond_maxsize():
    eng = _make_engine(maxsize=4)
    for i in range(20):
        eng._get_embedding_cached(f"k{i}")
    assert len(eng.embedding_cache) == 4
    # The four most recent should survive (k16..k19).
    surviving = set(eng.embedding_cache.keys())
    assert {hash(f"k{i}") for i in range(16, 20)} == surviving


def test_predict_uses_lru_path(monkeypatch):
    """Sanity check: predict() promotes-on-hit through the same LRU."""
    import asyncio

    eng = _make_engine(maxsize=3)
    eng.category_prototypes = {
        "food": {"prototype": np.array([1.0], dtype=np.float32)},
        "travel": {"prototype": np.array([-1.0], dtype=np.float32)},
    }
    eng.model_version = "test"
    eng.onnx_session = None

    async def run():
        r1 = await eng.predict("coffee shop")
        r2 = await eng.predict("coffee shop")  # hit
        return r1, r2

    r1, r2 = asyncio.run(run())
    assert r1["label"] in {"food", "travel"}
    assert r2["label"] == r1["label"]
    assert eng.inference_stats["cache_hits"] >= 1
