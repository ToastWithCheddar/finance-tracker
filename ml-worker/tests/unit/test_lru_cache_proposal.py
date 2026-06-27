"""Target LRU semantics for the future embedding cache.

`ml-worker/optimized_inference_engine.py:204-209` currently uses **FIFO**
eviction (`del self.embedding_cache[next(iter(self.embedding_cache))]`). Per
`docs/audit/improvement-sections/F-ml-worker-revival.md` task 3, this should
become a real LRU (move-to-end on hit, evict least-recently-used).

These tests pin down the contract Section F's implementation must satisfy.
The stub `_LRU` lives in this test file — when Section F lands, replace the
import with the real `EmbeddingCache` and these tests should still pass
without modification (modulo the constructor signature).
"""

from __future__ import annotations

from collections import OrderedDict

import pytest


class _LRU:
    """Minimal reference LRU used to validate the contract.

    Section F should replace `optimized_inference_engine.EmbeddingCache` with
    something that satisfies these same assertions.
    """

    def __init__(self, maxsize: int) -> None:
        if maxsize <= 0:
            raise ValueError("maxsize must be positive")
        self._maxsize = maxsize
        self._data: "OrderedDict[str, object]" = OrderedDict()

    def get(self, key: str):
        if key not in self._data:
            return None
        self._data.move_to_end(key)  # most-recently-used
        return self._data[key]

    def put(self, key: str, value) -> None:
        if key in self._data:
            self._data.move_to_end(key)
            self._data[key] = value
            return
        if len(self._data) >= self._maxsize:
            self._data.popitem(last=False)  # evict LRU
        self._data[key] = value

    def __len__(self) -> int:
        return len(self._data)

    def keys_in_order(self):
        """Oldest-first ordering — useful for assertions."""
        return list(self._data.keys())


def test_put_and_get_round_trip() -> None:
    cache = _LRU(maxsize=3)
    cache.put("a", 1)
    assert cache.get("a") == 1
    assert cache.get("missing") is None


def test_get_promotes_entry_to_mru() -> None:
    cache = _LRU(maxsize=3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    assert cache.keys_in_order() == ["a", "b", "c"]

    cache.get("a")  # touch oldest -> becomes MRU
    assert cache.keys_in_order() == ["b", "c", "a"]


def test_eviction_drops_least_recently_used() -> None:
    cache = _LRU(maxsize=2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.get("a")  # 'a' is now MRU; 'b' is LRU
    cache.put("c", 3)  # should evict 'b'

    assert cache.get("b") is None
    assert cache.get("a") == 1
    assert cache.get("c") == 3
    assert len(cache) == 2


def test_repeated_put_does_not_grow_beyond_maxsize() -> None:
    cache = _LRU(maxsize=4)
    for i in range(100):
        cache.put(f"k{i}", i)
    assert len(cache) == 4
    # The four most recent keys survive.
    assert cache.keys_in_order() == ["k96", "k97", "k98", "k99"]


def test_overwrite_existing_key_promotes_and_does_not_evict() -> None:
    cache = _LRU(maxsize=2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("a", 99)  # overwrite -> 'a' becomes MRU, no eviction

    assert len(cache) == 2
    assert cache.get("a") == 99
    assert cache.get("b") == 2


def test_maxsize_must_be_positive() -> None:
    with pytest.raises(ValueError):
        _LRU(maxsize=0)
    with pytest.raises(ValueError):
        _LRU(maxsize=-1)
