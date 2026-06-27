"""Proposed confidence-bucket helper.

Per `docs/audit/improvement-sections/F-ml-worker-revival.md` task 5:

    >= 0.75 -> "high"
    >= 0.55 -> "medium"
    else    -> "low"

This file is the canonical location *for now*. Section F will inline this
logic into `ml_classification_service.classify_transaction` and
`ml_classification_service.batch_classify`, replacing the hardcoded
``confidence_level = "high"`` (Demo mode) assignments documented in
`docs/audit/snapshot/ml-worker-map.md`.
"""

from __future__ import annotations

HIGH_THRESHOLD: float = 0.75
MEDIUM_THRESHOLD: float = 0.55


def bucket(similarity: float) -> str:
    """Map a cosine similarity in [-1.0, 1.0] to a confidence bucket.

    NaN inputs raise ``ValueError`` rather than silently returning "low" —
    a NaN here typically signals a degenerate prototype/embedding upstream
    and should fail loudly.
    """
    if similarity != similarity:  # NaN check without importing math
        raise ValueError("similarity is NaN")
    if similarity >= HIGH_THRESHOLD:
        return "high"
    if similarity >= MEDIUM_THRESHOLD:
        return "medium"
    return "low"
