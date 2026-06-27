"""BE-SEC-009 — Unbounded /api/transactions/export DoS risk.

`backend/app/routes/transactions.py:118-120` exposes GET /api/transactions/export
with no row cap and no rate limit. A single request with a wide date range can
stream the entire user's transaction history and tie up a worker indefinitely.

This test asserts the *hardened* behaviour:

1. A single request spanning ~100 years should be either
   - bounded by a row cap (response truncated; ideally a header announces it),
   - OR rejected with 4xx (e.g. 400 for unrealistic range, 413 too large), or
   - rate limited (429) when fired in rapid succession.

2. A burst of export requests must produce at least one 429 — the export
   endpoint is expensive and unauthenticated bursts are a textbook DoS.

xfail strict=False until the fix lands.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from factories import AccountFactory, CategoryFactory, TransactionFactory, UserFactory
from helpers.auth_client import make_authenticated_client


@pytest.mark.security
@pytest.mark.xfail(strict=False, reason="BE-SEC-009: /transactions/export unbounded")
def test_export_huge_range_is_capped_or_rejected(app_client, db_session):
    user = UserFactory.create()
    acct = AccountFactory.create(user=user)
    cat = CategoryFactory.create(user=user)
    # Seed a small but non-trivial number of rows so the endpoint has work to do.
    for i in range(50):
        TransactionFactory.create(user=user, account=acct, category=cat)

    client = make_authenticated_client(app_client, user)

    far_past = (datetime.now(timezone.utc) - timedelta(days=365 * 100)).isoformat()
    far_future = (datetime.now(timezone.utc) + timedelta(days=365 * 5)).isoformat()

    r = client.get(
        "/api/transactions/export",
        params={"format": "csv", "start_date": far_past, "end_date": far_future},
    )

    # Acceptable hardened outcomes: 400/413/422/429 reject, OR 200 with a row
    # cap surfaced in headers/body. We FAIL only if it's 200 AND no cap header
    # is present AND the body is unbounded (we approximate "unbounded" as
    # >100 KB returned for a 50-row seed; with a cap the body should be small).
    if r.status_code in (400, 413, 422, 429):
        return  # hardened — bounded by validation or rate limit

    assert r.status_code == 200, r.text
    cap_header = (
        r.headers.get("X-Row-Cap")
        or r.headers.get("X-Truncated")
        or r.headers.get("X-Export-Limit")
    )
    assert cap_header is not None, (
        "BE-SEC-009 regression: /transactions/export returned 200 over a "
        "100-year date range with no row-cap header. Endpoint is unbounded."
    )


@pytest.mark.security
@pytest.mark.xfail(strict=False, reason="BE-SEC-009: no rate limit on export")
def test_export_burst_is_rate_limited(app_client, db_session):
    user = UserFactory.create()
    AccountFactory.create(user=user)
    client = make_authenticated_client(app_client, user)

    statuses = []
    for _ in range(25):
        r = client.get("/api/transactions/export", params={"format": "csv"})
        statuses.append(r.status_code)

    assert 429 in statuses, (
        f"BE-SEC-009 regression: 25 sequential export requests produced no 429. "
        f"Status counts: { {s: statuses.count(s) for s in set(statuses)} }"
    )
