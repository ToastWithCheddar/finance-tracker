"""Categories router (`/api/categories`).

Routes:
- GET  /api/categories/             list (system + user)
- GET  /api/categories/system       system categories only
- GET  /api/categories/my           the current user's categories
- GET  /api/categories/hierarchy    hierarchical view
- POST /api/categories/             create custom category
"""

from __future__ import annotations

import pytest

from factories import CategoryFactory, UserFactory
from helpers.auth_client import make_authenticated_client


@pytest.fixture
def authed(app_client, db_session):
    user = UserFactory.create()
    client = make_authenticated_client(app_client, user)
    return client, user


@pytest.mark.integration
def test_list_categories(authed):
    client, user = authed
    CategoryFactory.create(user=user, name="Custom Cat A")

    r = client.get("/api/categories/")
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body, list)


@pytest.mark.integration
def test_create_custom_category(authed):
    client, _ = authed
    payload = {
        "name": "Subscriptions",
        "description": "Monthly recurring",
        "emoji": "📅",
        "color": "#3366ff",
        "sort_order": 5,
    }
    r = client.post("/api/categories/", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "Subscriptions"


@pytest.mark.integration
def test_create_duplicate_category_rejected(authed):
    client, user = authed
    CategoryFactory.create(user=user, name="Duplicate")

    r = client.post("/api/categories/", json={"name": "Duplicate"})
    assert r.status_code == 400, r.text


@pytest.mark.integration
def test_categories_hierarchy(authed):
    client, _ = authed
    r = client.get("/api/categories/hierarchy")
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), list)


@pytest.mark.integration
def test_my_categories(authed):
    client, user = authed
    CategoryFactory.create(user=user, name="Mine A")
    CategoryFactory.create(user=user, name="Mine B")

    r = client.get("/api/categories/my", params={"include_system": "false"})
    assert r.status_code == 200, r.text
    body = r.json()
    names = {c["name"] for c in body}
    assert {"Mine A", "Mine B"}.issubset(names)
