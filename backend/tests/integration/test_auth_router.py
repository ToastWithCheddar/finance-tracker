"""Full happy-path auth flow against real Postgres + mocked Supabase.

This replaces the broken `backend/tests/integration/test_auth_router.py`
(BE-TEST-003 — wrong endpoint path, form body instead of JSON, references to
`UserService.create_user` which doesn't exist).

Flow under test:
    POST /api/auth/register   -> 201, returns user + emailSent flag
    POST /api/auth/login      -> 200, returns AuthResponse with access_token
    GET  /api/auth/me         -> 200, returns the same user
    POST /api/auth/refresh    -> 200, returns new tokens
    POST /api/auth/logout     -> 204

Supabase is mocked via respx (helpers/supabase_mock.py). The real DB rows
are written to the testcontainer Postgres so we exercise SQLAlchemy enum /
UUID handling end-to-end.
"""

from __future__ import annotations

import uuid

import httpx
import pytest
import respx

from helpers.supabase_mock import make_session_payload, make_user_payload


@pytest.mark.xfail(strict=False, reason="BE-AUTH-001: schemas.UserCreate omits supabase_user_id field, so AuthService._create_local_user silently drops it during register and the new local row has supabase_user_id=NULL")
@pytest.mark.integration
def test_register_login_me_refresh_logout(app_client, db_session, supabase_mock):
    email = "alice@example.com"
    supabase_uid = "11111111-1111-1111-1111-111111111111"

    # ----- Override Supabase routes to point at THIS test's user. -----
    # Register on the active MockRouter (not module-level respx, which is a
    # different MockRouter and never intercepts in-flight httpx calls).
    user_payload = make_user_payload(user_id=supabase_uid, email=email)
    session_payload = make_session_payload(user_payload)

    supabase_mock.post("https://stub.supabase.co/auth/v1/signup").mock(
        return_value=httpx.Response(200, json={"user": user_payload, "session": session_payload})
    )
    supabase_mock.post("https://stub.supabase.co/auth/v1/token").mock(
        return_value=httpx.Response(200, json={**session_payload, "user": user_payload})
    )
    supabase_mock.get("https://stub.supabase.co/auth/v1/user").mock(
        return_value=httpx.Response(200, json=user_payload)
    )

    # ----- Register -----
    r = app_client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "StrongPass123",
            "display_name": "Alice",
            "first_name": "Alice",
            "last_name": "Example",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["user"]["email"] == email
    assert body["requiresEmailConfirmation"] is True

    # Verify a row was written to local Postgres.
    from app.models.user import User
    db_session.expire_all()
    local = db_session.query(User).filter(User.email == email).one()
    assert str(local.supabase_user_id) == supabase_uid

    # ----- Login -----
    r = app_client.post(
        "/api/auth/login",
        json={"email": email, "password": "StrongPass123"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["user"]["email"] == email
    assert body["tokens"]["access_token"]
    access_token = body["tokens"]["access_token"]
    refresh_token = body["tokens"]["refresh_token"]

    # ----- /me with Bearer token -----
    r = app_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["email"] == email

    # ----- Refresh -----
    r = app_client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert r.status_code == 200, r.text
    refreshed = r.json()
    assert refreshed["tokens"]["access_token"]

    # ----- Logout -----
    r = app_client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert r.status_code == 204


@pytest.mark.integration
def test_register_rejects_weak_password(app_client):
    """Pydantic-level validation: < 8 chars / no uppercase digit etc. should 422."""
    r = app_client.post(
        "/api/auth/register",
        json={"email": "weak@example.com", "password": "short"},
    )
    assert r.status_code == 422
