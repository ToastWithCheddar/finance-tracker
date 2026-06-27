"""Contract test — Plaid `/link/token/create` request shape.

Pins the exact request body our `PlaidClientService.create_link_token` sends
to Plaid. If a future refactor accidentally drops a field (e.g. `client_id`,
`secret`, `user.client_user_id`, `country_codes`, `language`, `client_name`),
this test fails loudly instead of producing a confusing 400 from Plaid only
in production.

The service uses `requests.post` (sync) wrapped in `loop.run_in_executor`,
so we intercept at the `requests.post` call boundary rather than via respx
(which mocks httpx). The intercept records the URL and JSON body so we can
assert structure.

Reference for fields:
  https://plaid.com/docs/api/tokens/#linktokencreate

Covers BE-SEC-006 (Plaid integration contract drift) tangentially and is
generally good defence against silent Plaid API breakage.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

_FIXTURE = Path(__file__).parent / "fixtures" / "plaid" / "link_token_response.json"


class _RecordedResponse:
    """Minimal stand-in for `requests.Response` — we only need .status_code,
    .json(), and .text to satisfy `_make_request`."""

    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


@pytest.mark.contract
def test_create_link_token_request_shape(monkeypatch):
    fixture = json.loads(_FIXTURE.read_text())

    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return _RecordedResponse(200, fixture)

    # Patch BEFORE importing the service so any module-level binding is fresh.
    import requests as _requests
    monkeypatch.setattr(_requests, "post", fake_post)

    from app.services.plaid_client_service import PlaidClientService
    from app.config import settings

    # Force the service to consider itself enabled with sane creds for the
    # duration of this test. Settings is a pydantic Settings instance — using
    # monkeypatch.setattr keeps the change scoped.
    monkeypatch.setattr(settings, "ENABLE_PLAID", True, raising=False)
    monkeypatch.setattr(settings, "PLAID_CLIENT_ID", "test-client-id", raising=False)
    monkeypatch.setattr(settings, "PLAID_SECRET", "test-secret", raising=False)
    monkeypatch.setattr(settings, "PLAID_ENV", "sandbox", raising=False)
    monkeypatch.setattr(settings, "PLAID_PRODUCTS", "transactions", raising=False)
    monkeypatch.setattr(settings, "PLAID_COUNTRY_CODES", "US", raising=False)

    svc = PlaidClientService()

    import asyncio
    result = asyncio.run(svc.create_link_token("user-uuid-abcdef"))

    assert result["success"] is True
    assert result["link_token"] == "link-sandbox-abc-123"

    # Now the meat: assert the body shape our backend sends.
    assert captured["url"].endswith("/link/token/create"), captured["url"]
    body = captured["json"]

    # Auth fields injected by `_make_request`.
    assert body["client_id"] == "test-client-id"
    assert body["secret"] == "test-secret"

    # Required Plaid fields.
    assert body["client_name"] == "Finance Tracker"
    assert body["country_codes"] == ["US"]
    assert body["language"] == "en"
    assert body["products"] == ["transactions"]

    # User block — `client_user_id` must be the string form of the user id.
    assert "user" in body, body
    assert body["user"]["client_user_id"] == "user-uuid-abcdef"

    # Headers should announce we are JSON.
    assert captured["headers"]["Content-Type"] == "application/json"
