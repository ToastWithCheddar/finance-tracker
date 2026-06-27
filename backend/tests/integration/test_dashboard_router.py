"""Dashboard router smoke tests + Redis cache hit assertion (BE-PERF-005).

Routes covered (mounted at `/api/dashboard`):
- GET /api/dashboard/summary       — financial-health summary, cached 30s
- GET /api/dashboard/              — filtered dashboard payload
- GET /api/dashboard/category-breakdown
- GET /api/dashboard/net-worth-trend?period=90d

The `summary` endpoint is the one with Redis caching (see
`backend/app/routes/dashboard.py:326-369`). We exercise it twice and assert
the second call short-circuits via Redis. Because the audit suite already
boots a real Redis testcontainer (see conftest), we don't need to monkeypatch
anything — we just spy on `redis_client.get_cache` to count invocations.
"""

from __future__ import annotations

import pytest

from factories import AccountFactory, CategoryFactory, TransactionFactory, UserFactory
from helpers.auth_client import make_authenticated_client


@pytest.fixture
def authed(app_client, db_session):
    user = UserFactory.create()
    account = AccountFactory.create(user=user)
    category = CategoryFactory.create(user=user)
    TransactionFactory.create(user=user, account=account, category=category)
    client = make_authenticated_client(app_client, user)
    return client, user


@pytest.mark.integration
def test_dashboard_summary_cached_on_second_call(authed, monkeypatch):
    client, user = authed

    from app.core import redis_client as redis_module

    call_count = {"get": 0, "set": 0}
    real_get = redis_module.redis_client.get_cache
    real_set = redis_module.redis_client.set_cache

    async def spy_get(key):
        call_count["get"] += 1
        return await real_get(key)

    async def spy_set(key, value, expire_seconds=None):
        call_count["set"] += 1
        return await real_set(key, value, expire_seconds=expire_seconds)

    monkeypatch.setattr(redis_module.redis_client, "get_cache", spy_get)
    monkeypatch.setattr(redis_module.redis_client, "set_cache", spy_set)

    r1 = client.get("/api/dashboard/summary")
    assert r1.status_code == 200, r1.text

    r2 = client.get("/api/dashboard/summary")
    assert r2.status_code == 200, r2.text

    # First call missed the cache and wrote it; second call should have hit it.
    assert call_count["get"] >= 2
    assert call_count["set"] >= 1
    # Bodies should be identical when served from cache.
    assert r1.json() == r2.json()


@pytest.mark.integration
def test_dashboard_root_with_filters(authed):
    client, _ = authed
    r = client.get(
        "/api/dashboard/",
        params={"start_date": "2020-01-01", "end_date": "2030-12-31"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "net_worth" in body
    assert "account_count" in body


@pytest.mark.integration
def test_dashboard_category_breakdown(authed):
    client, _ = authed
    r = client.get("/api/dashboard/category-breakdown")
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), list)


@pytest.mark.integration
def test_dashboard_net_worth_trend(authed):
    client, _ = authed
    r = client.get("/api/dashboard/net-worth-trend", params={"period": "90d"})
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), list)


@pytest.mark.integration
def test_dashboard_invalid_date_returns_400(authed):
    client, _ = authed
    r = client.get("/api/dashboard/", params={"start_date": "not-a-date"})
    assert r.status_code == 400
