"""ML categorize tasks. Targets BE-PERF-001 (event-loop blocking on Celery .get).

NOTE: This requires the ml-worker + Celery broker to be running. It is opt-in
via env var ``BENCH_INCLUDE_ML=1`` in ``locustfile.py``.
"""
from __future__ import annotations

import random

from locust import task, TaskSet

from tasks.auth import auth_headers


_MERCHANTS = [
    "Starbucks", "Whole Foods", "Shell", "Amazon", "Uber",
    "Netflix", "Spotify", "Costco", "Target", "Apple",
]
_DESCRIPTIONS = [
    "coffee morning", "weekly grocery run", "fuel fill-up",
    "online order", "ride home", "monthly subscription",
    "supplies", "household", "electronics", "office lunch",
]


class MLTaskSet(TaskSet):
    @task(1)
    def categorize(self):
        token = getattr(self.user, "token", None)
        if not token:
            return
        payload = {
            "description": random.choice(_DESCRIPTIONS),
            "merchant": random.choice(_MERCHANTS),
            "amount_cents": random.choice([-499, -1299, -2499, -5999]),
        }
        self.client.post(
            "/api/ml/categorize",
            json=payload,
            headers=auth_headers(token),
            name="POST /api/ml/categorize",
        )
