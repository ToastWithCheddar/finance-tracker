"""BE-RL-001 — SlowAPI mounted but no @limiter.limit applied.

`backend/app/main.py` mounts SlowAPI but no route is decorated. /auth/login
should be rate-limited. We hammer it 30 times and assert at least one
response comes back as 429. xfail until limits are applied.
"""

from __future__ import annotations

import pytest


@pytest.mark.security
@pytest.mark.xfail(strict=False, reason="BE-RL-001: zero @limiter.limit applied")
def test_login_rate_limited_after_threshold(app_client):
    statuses = []
    for _ in range(30):
        r = app_client.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": "WrongPass1!"},
        )
        statuses.append(r.status_code)

    assert 429 in statuses, (
        f"BE-RL-001 regression: 30 sequential login attempts produced no 429. "
        f"Status counts: { {s: statuses.count(s) for s in set(statuses)} }"
    )


@pytest.mark.security
@pytest.mark.xfail(strict=False, reason="BE-RL-001: zero @limiter.limit applied")
def test_register_rate_limited(app_client):
    statuses = []
    for i in range(30):
        r = app_client.post(
            "/api/auth/register",
            json={
                "email": f"throwaway{i}@example.com",
                "password": "StrongPass123",
            },
        )
        statuses.append(r.status_code)

    assert 429 in statuses
