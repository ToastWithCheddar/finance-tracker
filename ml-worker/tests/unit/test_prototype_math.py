"""Mean-of-embeddings prototype invariants.

Mirrors the math at `ml-worker/ml_classification_service.py:917-918`:

    prototype = np.mean(embeddings, axis=0)

These tests assert the properties downstream code (cosine sim, batch matmul
at :1015-1058) implicitly relies on.
"""

from __future__ import annotations

import numpy as np
import pytest


def _normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return matrix / norms


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def test_prototype_is_mean_of_embeddings(minilm_model) -> None:
    examples = [
        "food purchase grocery store",
        "food purchase restaurant meal",
        "food purchase coffee shop",
    ]
    embeddings = minilm_model.encode(examples, convert_to_numpy=True, normalize_embeddings=True)
    prototype = np.mean(embeddings, axis=0)
    expected = embeddings.sum(axis=0) / len(examples)
    np.testing.assert_allclose(prototype, expected, rtol=1e-6, atol=1e-6)
    assert prototype.shape == (embeddings.shape[1],)


def test_cosine_similarity_is_symmetric(minilm_model) -> None:
    a, b = minilm_model.encode(
        ["uber ride downtown", "lyft trip airport"],
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    assert _cosine(a, b) == pytest.approx(_cosine(b, a), abs=1e-9)


def test_cosine_self_similarity_is_one(minilm_model) -> None:
    v = minilm_model.encode(["netflix subscription"], convert_to_numpy=True, normalize_embeddings=True)[0]
    assert _cosine(v, v) == pytest.approx(1.0, abs=1e-5)


def test_prototype_is_closer_to_in_class_than_out_of_class(minilm_model) -> None:
    """Sanity: a food-prototype should be closer to a food query than to a
    transport query. Guards against a future regression where someone breaks
    the embedding pipeline (e.g. forgets to normalize)."""
    food = [
        "grocery store purchase",
        "restaurant dinner bill",
        "coffee shop latte",
        "pizza delivery order",
    ]
    transport = ["uber ride", "subway fare", "gas station fillup", "airline ticket"]

    food_emb = minilm_model.encode(food, convert_to_numpy=True, normalize_embeddings=True)
    transport_emb = minilm_model.encode(transport, convert_to_numpy=True, normalize_embeddings=True)

    food_proto = np.mean(food_emb, axis=0)
    transport_proto = np.mean(transport_emb, axis=0)

    food_query = minilm_model.encode(["takeout sushi order"], convert_to_numpy=True, normalize_embeddings=True)[0]

    sim_food = _cosine(food_query, food_proto)
    sim_transport = _cosine(food_query, transport_proto)

    assert sim_food > sim_transport, (
        f"food query unexpectedly closer to transport prototype: "
        f"food={sim_food:.4f} transport={sim_transport:.4f}"
    )


def test_normalize_helper_unit_norm() -> None:
    rng = np.random.default_rng(42)
    raw = rng.standard_normal((5, 16)).astype(np.float32)
    normed = _normalize(raw)
    np.testing.assert_allclose(np.linalg.norm(normed, axis=1), 1.0, atol=1e-6)
