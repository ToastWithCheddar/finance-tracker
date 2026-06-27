"""ML router — `/api/ml/categorize`.

The handler at `backend/app/routes/ml.py:42-99` calls
`celery_app.send_task('worker.classify_transaction', ...)` and then awaits
`AsyncResult.get(timeout=30)` on a worker thread. Without a running ml-worker,
that call blocks forever, so we monkeypatch `celery_app.send_task` to return a
fake AsyncResult whose `.get()` returns a deterministic dict.

We don't try to assert on the fallback HTTP path (`get_ml_client()`) — it only
fires when Celery raises, and we want the happy path here.
"""

from __future__ import annotations

import pytest

from factories import UserFactory
from helpers.auth_client import make_authenticated_client


class _FakeAsyncResult:
    def __init__(self, payload):
        self._payload = payload

    def get(self, timeout=None):
        return self._payload


@pytest.fixture
def authed(app_client, db_session):
    user = UserFactory.create()
    client = make_authenticated_client(app_client, user)
    return client, user


@pytest.mark.integration
def test_ml_categorize_uses_celery_task(authed, monkeypatch):
    client, _ = authed

    from app.routes import ml as ml_module

    captured = {}

    def fake_send_task(task_name, args=None, **kwargs):
        captured["task_name"] = task_name
        captured["args"] = args
        return _FakeAsyncResult(
            {
                "predicted_category": "11111111-1111-1111-1111-111111111111",
                "confidence": 0.92,
                "confidence_level": "high",
                "model_version": "test-v1",
                "all_similarities": {"food": 0.92, "rent": 0.04},
            }
        )

    monkeypatch.setattr(ml_module.celery_app, "send_task", fake_send_task)

    r = client.post(
        "/api/ml/categorize",
        json={
            "description": "Blue Bottle Coffee",
            "amount_cents": -650,
            "merchant": "Blue Bottle",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert body["data"]["confidence_level"] == "high"
    assert body["data"]["model_version"] == "test-v1"

    # Assert we hit the right Celery task.
    assert captured["task_name"] == "worker.classify_transaction"
    payload = captured["args"][0]
    assert payload["description"] == "Blue Bottle Coffee"
    assert payload["merchant"] == "Blue Bottle"
    assert payload["amount"] == -6.5  # cents converted to dollars


@pytest.mark.integration
def test_ml_categorize_validates_request_body(authed):
    """description is required and min_length=1."""
    client, _ = authed
    r = client.post("/api/ml/categorize", json={"amount_cents": -100})
    assert r.status_code == 422
