"""Helpers for ml-worker audit tests.

Currently exposes the proposed confidence-bucket function. Section F
(`docs/audit/improvement-sections/F-ml-worker-revival.md`, task 5) will move
this implementation into `ml-worker/ml_classification_service.py` to replace
the hardcoded ``confidence_level = "high"`` assignments at lines 984 and 1043.
"""

from .confidence import bucket

__all__ = ["bucket"]
