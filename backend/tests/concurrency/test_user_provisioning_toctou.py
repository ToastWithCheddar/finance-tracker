"""BE-CONC-001 — User provisioning TOCTOU on first login.

`backend/app/auth/dependencies.py:32-72` does:

    existing = user_service.get_by_email(email)
    if not existing:
        user_service.create(...)

If two requests for the same brand-new Supabase user arrive concurrently,
both threads see `existing is None`, both call `create()`, and the second
INSERT either races to a duplicate row or trips a unique constraint at
flush time — neither is "exactly one user".

Test strategy:
- Stub the Supabase `GET /auth/v1/user` route to always return the SAME
  user payload (id + email).
- Fire two `/api/auth/me` requests concurrently using httpx.AsyncClient
  + `asyncio.gather`.
- After both return, query the DB: there must be exactly one row with
  that email.

xfail strict=False per BE-CONC-001 until provisioning uses
`INSERT ... ON CONFLICT DO NOTHING` or `session.merge()` / advisory lock.
"""

from __future__ import annotations

import asyncio
import uuid

import httpx
import pytest
import respx

from app.models.user import User


@pytest.mark.concurrency
def test_concurrent_first_login_creates_exactly_one_user(app_client, db_session, supabase_mock):
    """Two parallel /api/auth/me hits for an unprovisioned Supabase user must
    yield exactly one local User row, not two."""

    new_supabase_id = str(uuid.uuid4())
    new_email = f"toctou-{uuid.uuid4().hex[:8]}@example.com"

    user_payload = {
        "id": new_supabase_id,
        "aud": "authenticated",
        "role": "authenticated",
        "email": new_email,
        "email_confirmed_at": "2024-01-01T00:00:00Z",
        "app_metadata": {"provider": "email"},
        "user_metadata": {"display_name": "TOCTOU User"},
        "identities": [],
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }

    # Override the default supabase mock route to return our brand-new user.
    # Must use the active MockRouter (yielded by the autouse `supabase_mock`
    # fixture); module-level `respx.get(...)` writes to a different router
    # and isn't consulted.
    supabase_mock.get("https://stub.supabase.co/auth/v1/user").mock(
        return_value=httpx.Response(200, json=user_payload)
    )

    base_url = str(app_client.base_url)
    headers = {"Authorization": "Bearer test-bearer-token"}

    async def _hit_me(client: httpx.AsyncClient):
        # AsyncClient against the in-process app via the WSGI/ASGI transport
        # the TestClient already wired up.
        return await client.get("/api/auth/me", headers=headers)

    async def _race():
        # Use the running TestClient's underlying ASGI app via httpx
        # ASGITransport so both requests share the same app + DB override.
        from app.main import app as _app

        transport = httpx.ASGITransport(app=_app)
        async with httpx.AsyncClient(transport=transport, base_url=base_url) as ac:
            return await asyncio.gather(_hit_me(ac), _hit_me(ac), return_exceptions=True)

    results = asyncio.run(_race())

    # At least one must succeed; the spec is "exactly one row", so we don't
    # care which thread "won" provisioning.
    rows = db_session.query(User).filter(User.email == new_email).all()
    assert len(rows) == 1, (
        f"BE-CONC-001 regression: expected exactly one user row for "
        f"{new_email}, got {len(rows)} (results={results!r})"
    )
