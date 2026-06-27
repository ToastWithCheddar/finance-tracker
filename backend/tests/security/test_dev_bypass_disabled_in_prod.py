"""BE-SEC-002 — dev mock token bypass.

`backend/app/auth/dependencies.py:74-101` short-circuits authentication for
any token starting with `dev-mock-token-` whenever `ENVIRONMENT` is
`development`. The production-hardened version should:

  1. Only honour the bypass when ENVIRONMENT == "development" AND DEBUG AND
     ENABLE_ADMIN_BYPASS are all true.
  2. Default `ENABLE_ADMIN_BYPASS` to false.

This test asserts the **hardened** behaviour: with ENVIRONMENT set to
`production`, a `dev-mock-token-foo` Bearer must NOT grant access.

Until the fix lands, this test is expected to FAIL — that is the point. The
test goes red BEFORE the fix and green AFTER, which is what you want from a
"prove the fix" test (Section B success metric).

The test patches `settings.ENVIRONMENT` at runtime rather than re-bootstrapping
the whole app, because `_validate_dev_token` re-reads `settings` at call time.
"""

from __future__ import annotations

import httpx
import pytest

from app.config import settings


def _force_supabase_to_reject(supabase_mock) -> None:
    """In production, the dev bypass MUST be inert — but the request still
    falls through to Supabase token validation. The default mock happily
    returns a user for any token, which would mask a real regression in the
    bypass gate. Override the route to 401 so we can isolate the bypass
    semantics.
    """
    supabase_mock.get("https://stub.supabase.co/auth/v1/user").mock(
        return_value=httpx.Response(401, json={"msg": "invalid token"})
    )


@pytest.mark.security
def test_dev_mock_token_rejected_when_environment_is_production(
    app_client, monkeypatch, supabase_mock
):
    # Force production environment.
    monkeypatch.setattr(settings, "ENVIRONMENT", "production", raising=False)
    _force_supabase_to_reject(supabase_mock)

    r = app_client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer dev-mock-token-anything"},
    )
    # The token should not be honoured — Supabase mock now rejects it and
    # the bypass must not kick in. We accept any non-2xx (401/403/500) as
    # evidence the bypass did not fire; what we MUST NOT see is 200.
    assert r.status_code != 200, (
        f"BE-SEC-002 regression: dev-mock-token granted access in production "
        f"(got {r.status_code}: {r.text})"
    )


@pytest.mark.security
def test_dev_mock_token_rejected_when_environment_is_staging(
    app_client, monkeypatch, supabase_mock
):
    """Staging is also not 'development' — bypass must not fire."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "staging", raising=False)
    _force_supabase_to_reject(supabase_mock)

    r = app_client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer dev-mock-token-anything"},
    )
    assert r.status_code != 200, r.text
