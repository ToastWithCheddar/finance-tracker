"""Transactions router smoke tests against real Postgres.

These tests exist primarily to prove that the audit suite can exercise
JSONB / ARRAY / Postgres enum columns — the things SQLite can't (BE-TEST-004).

We hit a small slice of `/api/transactions`:
- POST /api/transactions
- GET  /api/transactions  (paginated)
- DELETE /api/transactions/{id}

Full coverage of `/histogram`, `/export`, `/import`, `/bulk-delete`,
`/search_transactions` is left to the next wave.
"""

from __future__ import annotations

from datetime import date

import pytest

from factories import AccountFactory, CategoryFactory, UserFactory
from helpers.auth_client import make_authenticated_client


@pytest.fixture
def authed(app_client, db_session):
    """A fresh user + account + category bound into the running DB."""
    user = UserFactory.create()
    account = AccountFactory.create(user=user)
    category = CategoryFactory.create(user=user)
    client = make_authenticated_client(app_client, user)
    return client, user, account, category


@pytest.mark.integration
def test_create_and_list_transaction(authed, db_session):
    client, user, account, category = authed

    r = client.post(
        "/api/transactions",
        json={
            "accountId": str(account.id),
            "categoryId": str(category.id),
            "amountCents": -1234,
            "currency": "USD",
            "description": "Coffee",
            "merchant": "Blue Bottle",
            "transactionDate": date.today().isoformat(),
            "tags": ["coffee", "morning"],
            "metadataJson": {"source": "audit-test"},
        },
        params={"notify": "false"},
    )
    assert r.status_code == 200, r.text
    created = r.json()
    assert created["amount_cents"] == -1234 or created.get("amountCents") == -1234

    # Listing should return at least our one row.
    r = client.get("/api/transactions")
    assert r.status_code == 200, r.text
    body = r.json()
    # Router uses TransactionListResponse with `transactions` + pagination metadata.
    assert "transactions" in body or "items" in body or isinstance(body, list)
    if isinstance(body, dict):
        items = body.get("transactions") or body.get("items") or []
    else:
        items = body
    assert len(items) >= 1
    assert any(item.get("description") == "Coffee" for item in items)


@pytest.mark.integration
def test_delete_transaction(authed, db_session):
    client, user, account, category = authed

    create = client.post(
        "/api/transactions",
        json={
            "accountId": str(account.id),
            "categoryId": str(category.id),
            "amountCents": -500,
            "description": "ToDelete",
            "transactionDate": date.today().isoformat(),
        },
        params={"notify": "false"},
    )
    assert create.status_code == 200, create.text
    txn_id = create.json().get("id") or create.json().get("transactionId")
    assert txn_id

    r = client.delete(f"/api/transactions/{txn_id}")
    # Router returns 200 or 204 depending on impl; both are acceptable.
    assert r.status_code in (200, 204), r.text

    # Re-fetching should now 404.
    r = client.get(f"/api/transactions/{txn_id}")
    assert r.status_code == 404
