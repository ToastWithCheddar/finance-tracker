"""Accounts router (`/api/accounts`).

Routes (from `backend/app/routes/accounts_basic.py`):
- GET  /api/accounts/                list user's accounts
- POST /api/accounts/                create account manually
- GET  /api/accounts/{id}            get one
- PUT  /api/accounts/{id}            update (rename, toggle is_active, etc.)
- DELETE /api/accounts/{id}          delete

`AccountCreate` requires `name`, `account_type`, and `user_id` (we pass the
authed user's id). `balance_cents` defaults to 0.
"""

from __future__ import annotations

import pytest

from factories import AccountFactory, UserFactory
from helpers.auth_client import make_authenticated_client


@pytest.fixture
def authed(app_client, db_session):
    user = UserFactory.create()
    client = make_authenticated_client(app_client, user)
    return client, user


@pytest.mark.integration
def test_list_accounts(authed):
    client, user = authed
    AccountFactory.create(user=user, name="Checking A")
    AccountFactory.create(user=user, name="Savings B", account_type="savings")

    r = client.get("/api/accounts/")
    assert r.status_code == 200, r.text
    items = r.json()
    assert len(items) >= 2
    names = {a["name"] for a in items}
    assert {"Checking A", "Savings B"}.issubset(names)


@pytest.mark.integration
def test_create_manual_account(authed):
    client, user = authed
    payload = {
        "name": "New Wallet",
        "account_type": "checking",
        "balance_cents": 25_000,
        "currency": "USD",
        "is_active": True,
        "user_id": str(user.id),
    }
    r = client.post("/api/accounts/", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "New Wallet"
    assert body["balance_cents"] == 25_000


@pytest.mark.integration
def test_update_account_rename(authed):
    client, user = authed
    acct = AccountFactory.create(user=user, name="Original Name")

    r = client.put(
        f"/api/accounts/{acct.id}",
        json={"name": "Renamed", "is_active": False},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["name"] == "Renamed"
    assert body["is_active"] is False


@pytest.mark.integration
def test_get_other_users_account_404(authed, db_session):
    """Cross-user access must not leak — `get_owned_account` should 404."""
    client, _ = authed
    other_user = UserFactory.create()
    other_acct = AccountFactory.create(user=other_user)

    r = client.get(f"/api/accounts/{other_acct.id}")
    assert r.status_code in (403, 404), r.text
