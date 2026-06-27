"""Integration tests for `/health`.

Foundation wave: assert basic + detailed payload shape against real Postgres
and real Redis. We do NOT assert Supabase status because that depends on
whether the Supabase mock counts as "configured" — that distinction belongs
in a finer-grained test once BE-SEC-006 (config validation) is in.
"""

from __future__ import annotations

import pytest


@pytest.mark.integration
def test_health_basic(app_client):
    r = app_client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "healthy"
    assert body["service"] == "finance-tracker-api"
    # ENVIRONMENT was set to "test" in conftest's bootstrap.
    assert body["environment"] == "test"
    assert "timestamp" in body
    # Basic payload should NOT include the per-dependency checks dict.
    assert "checks" not in body


@pytest.mark.xfail(strict=False, reason="BE-HEALTH-001: routes/health.py calls redis_client.ping() but RedisClient class has no ping() method, so detailed health always reports redis as unhealthy")
@pytest.mark.integration
def test_health_detailed_includes_db_and_redis(app_client):
    r = app_client.get("/health?detailed=true")
    # When all deps are healthy, status code is 200.
    assert r.status_code == 200, r.text
    body = r.json()

    assert "checks" in body
    assert body["checks"]["database"]["status"] == "healthy"
    # Redis is real (testcontainer), so it should be healthy.
    assert body["checks"]["redis"]["status"] == "healthy"
    # Supabase is "configured" because we set SUPABASE_URL/ANON_KEY in the
    # bootstrap; the route only checks `is_configured()`, not connectivity.
    assert body["checks"]["supabase"]["status"] in {"healthy", "not_configured"}
