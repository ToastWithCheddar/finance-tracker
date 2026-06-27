"""Users router (`/api/users`).

Routes covered:
- GET  /api/users/me         current user profile
- PUT  /api/users/me         update profile (UserUpdate schema)
- GET  /api/users/me/profile public profile view
"""

from __future__ import annotations

import pytest

from factories import UserFactory
from helpers.auth_client import make_authenticated_client


@pytest.fixture
def authed(app_client, db_session):
    user = UserFactory.create()
    client = make_authenticated_client(app_client, user)
    return client, user


@pytest.mark.integration
def test_get_me(authed):
    client, user = authed
    r = client.get("/api/users/me")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["email"] == user.email


@pytest.mark.integration
def test_update_me_profile(authed):
    client, user = authed
    # NOTE: UserUpdate schema accepts display_name/timezone/etc. but NOT
    # first_name/last_name (those live on the model only). Use the fields the
    # schema actually exposes.
    r = client.put(
        "/api/users/me",
        json={"display_name": "Updated Name", "timezone": "America/New_York"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["display_name"] == "Updated Name"
    assert body["timezone"] == "America/New_York"


@pytest.mark.integration
def test_me_profile_public_view(authed):
    client, _ = authed
    r = client.get("/api/users/me/profile")
    assert r.status_code == 200, r.text
