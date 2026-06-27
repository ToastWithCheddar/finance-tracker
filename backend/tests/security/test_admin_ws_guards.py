"""BE-SEC-007 — Admin WS endpoints lack admin guard.

A focused security mirror of `integration/test_websockets_router.py`'s xfail
cases. Lives here so a `pytest -m security` invocation surfaces the finding
even when integration tests are skipped (e.g. in a fast pre-commit lane).
"""

from __future__ import annotations

import pytest

from factories import UserFactory
from helpers.auth_client import make_authenticated_client


@pytest.mark.security
@pytest.mark.xfail(strict=False, reason="BE-SEC-007: admin WS endpoints lack admin guard")
@pytest.mark.parametrize(
    "method,path,extra",
    [
        ("get", "/ws/stats", {}),
        ("post", "/ws/broadcast", {"params": {"message_type": "x"}, "json": {}}),
        ("post", "/ws/test-message/some-uid", {"params": {"message_type": "x"}, "json": {}}),
    ],
)
def test_admin_ws_endpoints_reject_non_admin(app_client, db_session, method, path, extra):
    user = UserFactory.create()  # non-admin
    client = make_authenticated_client(app_client, user)

    r = getattr(client, method)(path, **extra)
    assert r.status_code == 403, (
        f"BE-SEC-007 regression: non-admin reached {method.upper()} {path} "
        f"(got {r.status_code})"
    )
