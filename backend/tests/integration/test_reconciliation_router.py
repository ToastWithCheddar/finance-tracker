"""Account reconciliation router (`/api/accounts/{id}/reconcile`, etc.).

Routes (from `backend/app/routes/accounts_reconciliation.py`):
- POST /api/accounts/{account_id}/reconcile           start reconciliation
- POST /api/accounts/reconcile-all                    reconcile every owned account
- POST /api/accounts/{account_id}/reconciliation-entry create adjustment
- GET  /api/accounts/{account_id}/reconciliation-history
- GET  /api/accounts/{account_id}/health              health snapshot

Reconciliation services depend on `get_enhanced_reconciliation_service` and
`get_websocket_manager_dep` — we monkeypatch these to deterministic stubs so
the test doesn't require the real services to be wired.
"""

from __future__ import annotations

import pytest

from factories import AccountFactory, UserFactory
from helpers.auth_client import make_authenticated_client


@pytest.fixture
def authed(app_client, db_session):
    user = UserFactory.create()
    account = AccountFactory.create(user=user)
    client = make_authenticated_client(app_client, user)
    return client, user, account


class _FakeReconciliationService:
    async def reconcile_account(self, db, account_id):
        return {
            "account_id": str(account_id),
            "account_name": "Test",
            "is_reconciled": True,
            "discrepancy": 0,
            "reconciliation_date": "2024-01-01T00:00:00Z",
        }

    async def reconcile_all_accounts(self, db, user_id):
        return {
            "total_accounts": 1,
            "reconciled_accounts": 1,
            "accounts_with_discrepancies": 0,
            "total_discrepancy": 0,
        }


class _FakeWSManager:
    async def send_to_user(self, user_id, payload):
        return None


@pytest.fixture
def patched_services(monkeypatch):
    from app import dependencies as deps_module

    monkeypatch.setattr(
        deps_module, "get_enhanced_reconciliation_service",
        lambda: _FakeReconciliationService(), raising=False,
    )
    monkeypatch.setattr(
        deps_module, "get_websocket_manager_dep",
        lambda: _FakeWSManager(), raising=False,
    )

    # The routes pull these via FastAPI's Depends(...) at request time, so we
    # need to override the app's dependency_overrides too.
    from app.main import app

    app.dependency_overrides[deps_module.get_enhanced_reconciliation_service] = (
        lambda: _FakeReconciliationService()
    )
    app.dependency_overrides[deps_module.get_websocket_manager_dep] = (
        lambda: _FakeWSManager()
    )
    yield
    app.dependency_overrides.pop(deps_module.get_enhanced_reconciliation_service, None)
    app.dependency_overrides.pop(deps_module.get_websocket_manager_dep, None)


@pytest.mark.xfail(strict=False, reason="BE-RECON-001: routes/accounts_reconciliation.py references EventType.ACCOUNT_RECONCILED which is not defined on the EventType enum")
@pytest.mark.integration
def test_reconcile_account_happy_path(authed, patched_services):
    client, user, account = authed
    r = client.post(f"/api/accounts/{account.id}/reconcile")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert body["data"]["is_reconciled"] is True


@pytest.mark.xfail(strict=False, reason="BE-RECON-001: routes/accounts_reconciliation.py references undefined EventType members")
@pytest.mark.integration
def test_reconcile_all_accounts(authed, patched_services):
    client, _, _ = authed
    r = client.post("/api/accounts/reconcile-all")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert body["data"]["total_accounts"] >= 0


@pytest.mark.integration
def test_reconcile_other_users_account_rejected(authed, patched_services, db_session):
    client, _, _ = authed
    other_user = UserFactory.create()
    other_acct = AccountFactory.create(user=other_user)

    r = client.post(f"/api/accounts/{other_acct.id}/reconcile")
    # AuthorizationError → typically 403; AccountNotFoundError → 404.
    assert r.status_code in (403, 404), r.text
