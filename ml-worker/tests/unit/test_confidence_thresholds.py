"""Section F (ML-PR-002): pin the 4-bucket confidence spec implemented in
`ml-worker/ml_classification_service.py::_confidence_bucket`.

Buckets:
    >= 0.85 -> "high"
    >= 0.65 -> "medium"
    >= 0.45 -> "low"
    <  0.45 -> "very_low"

Note: the 3-bucket helper at `ml-worker/tests/helpers/confidence.py`
encodes the *original* Section F draft (0.75 / 0.55). Wave 8 chose the wider
4-bucket scheme so downstream gating can distinguish "weak" from "no signal".
This test pins the production constants to avoid silent regressions.
"""

from __future__ import annotations

import math

import pytest


@pytest.fixture(scope="module")
def bucket_fn():
    from ml_classification_service import _confidence_bucket
    return _confidence_bucket


@pytest.mark.parametrize(
    "score, expected",
    [
        (1.00, "high"),
        (0.95, "high"),
        (0.85, "high"),  # exact boundary
        (0.8499, "medium"),
        (0.70, "medium"),
        (0.65, "medium"),  # exact boundary
        (0.6499, "low"),
        (0.50, "low"),
        (0.45, "low"),  # exact boundary
        (0.4499, "very_low"),
        (0.0, "very_low"),
        (-0.5, "very_low"),
        (-1.0, "very_low"),
    ],
)
def test_confidence_buckets(bucket_fn, score, expected):
    assert bucket_fn(score) == expected


def test_nan_raises(bucket_fn):
    with pytest.raises(ValueError):
        bucket_fn(float("nan"))


def test_thresholds_pinned():
    from ml_classification_service import _CONF_HIGH, _CONF_MEDIUM, _CONF_LOW
    assert _CONF_HIGH == 0.85
    assert _CONF_MEDIUM == 0.65
    assert _CONF_LOW == 0.45


def test_monotonic_ordering(bucket_fn):
    rank = {"very_low": 0, "low": 1, "medium": 2, "high": 3}
    samples = sorted([-1.0, 0.0, 0.4, 0.45, 0.5, 0.65, 0.7, 0.85, 1.0])
    ranks = [rank[bucket_fn(s)] for s in samples]
    assert ranks == sorted(ranks)
    assert not any(math.isnan(s) for s in samples)
