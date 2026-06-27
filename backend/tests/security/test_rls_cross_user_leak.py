"""BE-SEC-001 — Broken Postgres RLS context manager.

`backend/app/auth/dependencies.py:225-231` uses `with user_context_db(...)`
that exits BEFORE the session is yielded. `SET LOCAL` is per-transaction, so
the row-level-security `app.current_user_id` GUC is lost the moment the
context manager exits and the route runs queries OUTSIDE any user context.

Result: User A's request can in principle see User B's rows.

We assert the *desired* behaviour: User A authed via /api/transactions can
only see User A's transactions, never User B's. xfail until the dependency
is restructured to yield inside the with-block.
"""

from __future__ import annotations

import pytest

from factories import AccountFactory, CategoryFactory, TransactionFactory, UserFactory
from helpers.auth_client import make_authenticated_client


@pytest.mark.security
def test_user_a_cannot_see_user_b_transactions(app_client, db_session):
    user_a = UserFactory.create()
    user_b = UserFactory.create()

    # Seed: user_b has a transaction we definitely don't want user_a to see.
    acct_b = AccountFactory.create(user=user_b)
    cat_b = CategoryFactory.create(user=user_b)
    secret = TransactionFactory.create(
        user=user_b,
        account=acct_b,
        category=cat_b,
        description="USER B SECRET TRANSACTION",
    )

    # user_a has their own transaction.
    acct_a = AccountFactory.create(user=user_a)
    cat_a = CategoryFactory.create(user=user_a)
    TransactionFactory.create(
        user=user_a, account=acct_a, category=cat_a, description="USER A OWN"
    )

    client_a = make_authenticated_client(app_client, user_a)

    r = client_a.get("/api/transactions", params={"page_size": 100})
    assert r.status_code == 200, r.text
    body = r.json()
    if isinstance(body, dict):
        items = body.get("transactions") or body.get("items") or []
    else:
        items = body

    descriptions = {item.get("description") for item in items}
    assert "USER B SECRET TRANSACTION" not in descriptions, (
        f"BE-SEC-001 leak: user A saw user B's row {secret.id}"
    )
    # Sanity: user_a should still see their own row.
    assert any("USER A OWN" in (d or "") for d in descriptions)
