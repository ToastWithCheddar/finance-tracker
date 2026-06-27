"""Authenticated TestClient helper.

Usage:

    from helpers.auth_client import make_authenticated_client

    def test_something(app_client, db_session):
        user = UserFactory.create()
        client = make_authenticated_client(app_client, user)
        r = client.get("/api/auth/me")
        assert r.status_code == 200

The default Supabase mock (helpers/supabase_mock.py) returns a fixed user
from `GET /auth/v1/user`. To make get_current_user resolve to *our* test
user, we override the Supabase get_user response to return that user's
supabase_user_id. The DB lookup then finds the local row and skips
auto-provisioning.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import respx

from .supabase_mock import make_session_payload, make_user_payload

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from app.models.user import User


_BEARER_TOKEN = "test-bearer-token"


def make_authenticated_client(client: "TestClient", user: "User") -> "TestClient":
    """Configure `client` so that requests carry an Authorization header
    that resolves to `user` via the Supabase mock.

    We mutate the existing client's headers rather than constructing a new
    one because TestClient created outside the `app_client` fixture wouldn't
    inherit the dependency overrides.
    """
    user_payload = make_user_payload(
        user_id=str(user.supabase_user_id) if user.supabase_user_id else "00000000-0000-0000-0000-000000000001",
        email=user.email,
        email_confirmed=user.is_verified,
    )

    # Re-route the get_user endpoint to return THIS user's id/email. The
    # autouse `supabase_mock` fixture in conftest.py already started a
    # respx.mock context and stashed the router at supabase_mock._ACTIVE_ROUTER.
    # We must register on that SAME router — `respx.get(...)` (module-level)
    # uses the global MockRouter, which is a different instance and never
    # actually intercepts the in-flight httpx request.
    from . import supabase_mock as _sb

    router = _sb._ACTIVE_ROUTER
    if router is None:
        # Fall back to global respx so this still does *something* if the
        # fixture wasn't installed (e.g. unit tests).
        router = respx
    router.get("https://stub.supabase.co/auth/v1/user").mock(
        return_value=httpx.Response(200, json=user_payload)
    )

    client.headers["Authorization"] = f"Bearer {_BEARER_TOKEN}"
    return client


def make_login_response(user: "User") -> dict:
    """Build a `/auth/v1/token` response that points at the given user.

    Used by tests that exercise the full login flow.
    """
    user_payload = make_user_payload(
        user_id=str(user.supabase_user_id) if user.supabase_user_id else "00000000-0000-0000-0000-000000000001",
        email=user.email,
        email_confirmed=user.is_verified,
    )
    session = make_session_payload(user_payload)
    return {**session, "user": user_payload}
