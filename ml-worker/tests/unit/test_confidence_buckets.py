"""Confidence-bucket thresholds (per F-ml-worker-revival.md task 5).

Production code currently hardcodes ``confidence_level = "high"`` at
`ml_classification_service.py:984` and `:1043` ("Demo mode"). Section F will
move the helper from `ml-worker/tests/helpers/confidence.py` into
the ml-worker source. These tests pin the threshold contract:

    >= 0.75 -> "high"
    >= 0.55 -> "medium"
    else    -> "low"
"""

from __future__ import annotations

import math

import pytest

from helpers.confidence import HIGH_THRESHOLD, MEDIUM_THRESHOLD, bucket


@pytest.mark.parametrize(
    "similarity, expected",
    [
        (1.00, "high"),
        (0.90, "high"),
        (0.7501, "high"),
        (HIGH_THRESHOLD, "high"),  # exact boundary -> high
        (0.7499, "medium"),
        (0.65, "medium"),
        (0.5501, "medium"),
        (MEDIUM_THRESHOLD, "medium"),  # exact boundary -> medium
        (0.5499, "low"),
        (0.30, "low"),
        (0.0, "low"),
        (-0.5, "low"),
        (-1.0, "low"),
    ],
)
def test_bucket_thresholds(similarity: float, expected: str) -> None:
    assert bucket(similarity) == expected


def test_thresholds_match_section_F_spec() -> None:
    # Pinned so a future "fix" to threshold values fails this test loudly.
    assert HIGH_THRESHOLD == 0.75
    assert MEDIUM_THRESHOLD == 0.55


def test_nan_raises() -> None:
    with pytest.raises(ValueError):
        bucket(float("nan"))


def test_returns_only_known_labels() -> None:
    allowed = {"high", "medium", "low"}
    for value in [-1.0, -0.1, 0.0, 0.3, 0.55, 0.6, 0.74, 0.75, 0.9, 1.0]:
        assert bucket(value) in allowed


def test_monotonic_non_decreasing_label_rank() -> None:
    rank = {"low": 0, "medium": 1, "high": 2}
    samples = sorted([-1.0, 0.0, 0.4, 0.55, 0.6, 0.7, 0.75, 0.85, 1.0])
    ranks = [rank[bucket(s)] for s in samples]
    assert ranks == sorted(ranks), f"bucket ranks not monotonic: {list(zip(samples, ranks))}"
    assert not any(math.isnan(s) for s in samples)
