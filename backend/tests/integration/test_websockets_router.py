"""WebSockets router — admin endpoints (BE-SEC-007).

`backend/app/routes/websockets.py:166-253` exposes:
- GET  /ws/stats
- POST /ws/test-message/{user_id}
- POST /ws/broadcast

All three currently require only `get_current_user_from_token` — no admin
guard. Per BE-SEC-007 the hardened version must reject non-admin callers with
403. This test asserts the *desired* behaviour and is xfail-marked until the
fix lands.
"""

from __future__ import annotations

import pytest

from factories import UserFactory
from helpers.auth_client import make_authenticated_client


@pytest.fixture
def authed_non_admin(app_client, db_session):
    user = UserFactory.create()  # is_admin defaults to False (no such column);
    client = make_authenticated_client(app_client, user)
    return client, user


@pytest.mark.integration
@pytest.mark.xfail(strict=False, reason="BE-SEC-007: admin WS endpoints lack admin guard")
def test_ws_stats_rejects_non_admin(authed_non_admin):
    client, _ = authed_non_admin
    r = client.get("/ws/stats")
    assert r.status_code == 403, f"BE-SEC-007 regression: got {r.status_code}"


@pytest.mark.integration
@pytest.mark.xfail(strict=False, reason="BE-SEC-007: admin WS endpoints lack admin guard")
def test_ws_broadcast_rejects_non_admin(authed_non_admin):
    client, _ = authed_non_admin
    r = client.post(
        "/ws/broadcast",
        params={"message_type": "info", "priority": "low"},
        json={"hello": "world"},
    )
    assert r.status_code == 403, f"BE-SEC-007 regression: got {r.status_code}"


@pytest.mark.integration
@pytest.mark.xfail(strict=False, reason="BE-SEC-007: admin WS endpoints lack admin guard")
def test_ws_test_message_rejects_non_admin(authed_non_admin):
    client, _ = authed_non_admin
    r = client.post(
        "/ws/test-message/some-user-id",
        params={"message_type": "info"},
        json={"x": 1},
    )
    assert r.status_code == 403, f"BE-SEC-007 regression: got {r.status_code}"


@pytest.mark.integration
def test_ws_health_is_unauthenticated_or_authenticated(authed_non_admin):
    """`/ws/health` is the only WS endpoint that should be open. Smoke test it."""
    client, _ = authed_non_admin
    r = client.get("/ws/health")
    # Accept 200 (open) OR 401/403 if a guard is added — we don't want to lock
    # the project into either interpretation.
    assert r.status_code in (200, 401, 403)
