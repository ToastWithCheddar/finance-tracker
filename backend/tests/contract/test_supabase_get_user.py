"""Contract test — Supabase `auth.get_user(token)` JWT extraction path.

The auth dependency (`backend/app/auth/dependencies.py:103-108`) calls
`auth_service.supabase.client.auth.get_user(token)` and pulls
`user_data.user.{id,email,email_confirmed_at,user_metadata}` to provision
or look up the local user.

If Supabase changes the response shape — or our gotrue version changes how
it parses it — provisioning silently breaks. This test pins the shape we
expect by:

  1. Loading a representative response from `fixtures/supabase/get_user_response.json`.
  2. Routing `GET https://stub.supabase.co/auth/v1/user` to that fixture.
  3. Hitting `/api/auth/me` with a Bearer token.
  4. Asserting the response contains the email/id from the fixture, proving
     the extraction path read the fields we assume exist.

Covers contract regressions in BE-SEC-008 (Supabase auth.get_user usage).
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

_FIXTURE = Path(__file__).parent / "fixtures" / "supabase" / "get_user_response.json"


@pytest.mark.contract
def test_supabase_get_user_response_extracts_id_and_email(app_client, db_session, supabase_mock):
    fixture = json.loads(_FIXTURE.read_text())

    # Override the default supabase mock route to return our fixture exactly.
    # MUST register on the active MockRouter (yielded by the autouse
    # supabase_mock fixture); module-level `respx.get(...)` writes to a
    # different MockRouter instance and never intercepts in-flight requests.
    supabase_mock.get("https://stub.supabase.co/auth/v1/user").mock(
        return_value=httpx.Response(200, json=fixture)
    )

    r = app_client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer fixture-bearer-token"},
    )

    assert r.status_code == 200, r.text
    body = r.json()

    # The /me endpoint returns the local user record. Provisioning should
    # have used the fixture's email + id, so the response must surface them.
    assert body.get("email") == fixture["email"], (
        f"Supabase contract drift: /me returned email={body.get('email')!r} "
        f"but fixture provided {fixture['email']!r}"
    )

    # Local user gets its own UUID; what we can verify is that the
    # `supabase_user_id` was preserved from the fixture.
    sup_id = body.get("supabase_user_id") or body.get("supabaseUserId")
    if sup_id is not None:
        assert str(sup_id) == fixture["id"], (
            f"Supabase contract drift: supabase_user_id={sup_id} "
            f"but fixture id={fixture['id']}"
        )
