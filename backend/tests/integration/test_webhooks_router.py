"""Webhooks router — Plaid signature verification (BE-SEC-006).

`backend/app/auth/dependencies.py:307` references
`settings.PLAID_BASE_URL` which IS NOT DEFINED in `app.config.Settings`. The
Plaid webhook flow therefore raises AttributeError before the JWT signature is
ever checked. This test asserts the *desired* behaviour: a forged
`Plaid-Verification` JWT must be rejected with 401, not crash the server with
500. xfail-marked until BE-SEC-006 is fixed.

We use respx to mock Plaid's JWKS endpoint so the test doesn't require a live
Plaid sandbox.
"""

from __future__ import annotations

import httpx
import pytest
import respx


@pytest.mark.integration
@pytest.mark.xfail(strict=False, reason="BE-SEC-006: settings.PLAID_BASE_URL undefined")
def test_plaid_webhook_rejects_forged_jwt(app_client, monkeypatch):
    # Pretend we have a Plaid base URL even though the app doesn't define one.
    from app.config import settings

    monkeypatch.setattr(settings, "PLAID_BASE_URL", "https://stub.plaid.com", raising=False)
    monkeypatch.setattr(settings, "PLAID_CLIENT_ID", "stub-client", raising=False)
    monkeypatch.setattr(settings, "PLAID_SECRET", "stub-secret", raising=False)

    respx.post("https://stub.plaid.com/webhook_verification_key/get").mock(
        return_value=httpx.Response(
            200,
            json={
                "keys": [
                    {
                        "kid": "stub-kid",
                        "alg": "ES256",
                        "kty": "EC",
                        "use": "sig",
                        "crv": "P-256",
                        "x": "f83OJ3D2xF1Bg8vub9tLe1gHMzV76e8Tus9uPHvRVEU",
                        "y": "x_FEzRu9m36HLN_tue659LNpXW6pCyStikYjKIWI5a0",
                    }
                ]
            },
        )
    )

    forged_jwt = (
        "eyJhbGciOiJFUzI1NiIsImtpZCI6InN0dWIta2lkIn0."
        "eyJpYXQiOjAsImlzcyI6ImZvcmdlZCJ9."
        "AAAA-not-a-real-signature"
    )

    r = app_client.post(
        "/api/webhooks/plaid",
        headers={"Plaid-Verification": forged_jwt},
        json={"webhook_type": "TRANSACTIONS", "webhook_code": "DEFAULT_UPDATE"},
    )
    assert r.status_code == 401, (
        f"Plaid webhook should reject forged JWT, got {r.status_code}: {r.text}"
    )


@pytest.mark.integration
def test_supabase_webhook_missing_secret_rejected(app_client):
    """Sanity: hitting /api/webhooks/supabase without the right secret returns 4xx."""
    r = app_client.post(
        "/api/webhooks/supabase",
        json={"type": "user.updated", "record": {"id": "00000000-0000-0000-0000-000000000001"}},
    )
    # Should fail signature verification at `verify_supabase_webhook`.
    assert r.status_code in (401, 403, 422)
