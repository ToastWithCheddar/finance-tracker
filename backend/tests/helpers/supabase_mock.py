"""respx mocks for Supabase auth endpoints.

The application talks to Supabase via supabase-py, which underneath uses
httpx against `${SUPABASE_URL}/auth/v1/*`. We mount our test SUPABASE_URL at
`https://stub.supabase.co` (see conftest.py); these routes intercept the
calls our backend makes during register / login / refresh / get_user.

We deliberately keep the response shapes minimal — just enough fields for
the gotrue Python client to deserialize. If a future test needs richer
shapes (e.g. user_metadata, identities), add them here, not inline.

Reference: https://supabase.com/docs/reference/javascript/auth-api (the REST
shape is the same regardless of language client).
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict

import httpx
import respx

# A stable user record we hand back from sign_up / login / get_user. Tests
# that need multiple users should call `make_user_payload(email=...)` and
# install their own routes on top.
DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_EMAIL = "test-user@example.com"

# Set by conftest.supabase_mock fixture so test helpers can register routes on
# the active MockRouter (rather than the global respx mock, which is a
# different MockRouter instance).
_ACTIVE_ROUTER: respx.MockRouter | None = None


def make_user_payload(
    user_id: str = DEFAULT_USER_ID,
    email: str = DEFAULT_EMAIL,
    *,
    email_confirmed: bool = True,
) -> Dict[str, Any]:
    return {
        "id": user_id,
        "aud": "authenticated",
        "role": "authenticated",
        "email": email,
        "email_confirmed_at": "2024-01-01T00:00:00Z" if email_confirmed else None,
        "phone": "",
        "confirmed_at": "2024-01-01T00:00:00Z" if email_confirmed else None,
        "last_sign_in_at": "2024-01-01T00:00:00Z",
        "app_metadata": {"provider": "email", "providers": ["email"]},
        "user_metadata": {"display_name": "Test User"},
        "identities": [],
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }


def make_session_payload(user: Dict[str, Any] | None = None) -> Dict[str, Any]:
    user = user or make_user_payload()
    # gotrue expects a JWT-shaped string; we hand back something that looks
    # JWT-ish so any code path that calls jwt.get_unverified_header doesn't
    # blow up. We do NOT sign it — verification is mocked via the get_user
    # endpoint below.
    fake_jwt = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."  # header
        "eyJzdWIiOiJzdHViIiwicm9sZSI6ImF1dGhlbnRpY2F0ZWQifQ."  # payload
        "stub-signature"  # signature
    )
    return {
        "access_token": fake_jwt,
        "token_type": "bearer",
        "expires_in": 3600,
        "expires_at": int(time.time()) + 3600,
        "refresh_token": f"refresh-{uuid.uuid4().hex}",
        "user": user,
    }


def install_default_routes(router: respx.MockRouter, base_url: str = "https://stub.supabase.co") -> None:
    """Install permissive default routes for Supabase auth.

    These routes are non-strict — `assert_all_called=False` means individual
    tests don't fail if they happen not to hit one. Tests that want to assert
    a specific call should add a `.mock(side_effect=...)` for the route they
    care about.
    """
    user = make_user_payload()
    session = make_session_payload(user)

    auth = f"{base_url}/auth/v1"

    # Sign up — Supabase returns the user (and a session if email confirm is off).
    router.post(f"{auth}/signup").mock(
        return_value=httpx.Response(200, json={"user": user, "session": session})
    )

    # Sign in with password (POST /token?grant_type=password).
    router.post(f"{auth}/token").mock(
        return_value=httpx.Response(200, json={**session, "user": user})
    )

    # Get user from token (GET /user with Bearer).
    router.get(f"{auth}/user").mock(return_value=httpx.Response(200, json=user))

    # Sign out.
    router.post(f"{auth}/logout").mock(return_value=httpx.Response(204))

    # Password reset.
    router.post(f"{auth}/recover").mock(return_value=httpx.Response(200, json={}))

    # Resend.
    router.post(f"{auth}/resend").mock(return_value=httpx.Response(200, json={}))

    # Update user (PUT /user).
    router.put(f"{auth}/user").mock(return_value=httpx.Response(200, json=user))
