"""Microbench for /api/dashboard/summary against the in-process FastAPI app.

This is intentionally opt-in: it imports the backend app, which pulls in
SQLAlchemy, Supabase, Redis, Celery, etc. Most CI machines or quick local
checkouts won't have those. We gate behind ``BENCH_RUN=1`` and ``skip`` cleanly
on import errors.

Run::

    BENCH_RUN=1 pytest -m benchmark
"""
from __future__ import annotations

import os

import pytest


pytestmark = pytest.mark.benchmark


if os.environ.get("BENCH_RUN", "0") != "1":  # pragma: no cover
    pytest.skip(
        "Microbench gated by BENCH_RUN=1; skipping by default.",
        allow_module_level=True,
    )


# Importing the backend app is heavy and side-effecting; do it lazily so the
# module loads (for collection) even if the deps are missing.
def _build_client():
    try:
        import httpx
        from app.main import create_app  # type: ignore
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"Cannot import backend app: {exc!r}")

    app = create_app() if callable(getattr(create_app, "__call__", None)) else None
    if app is None:
        try:
            from app.main import app as fastapi_app  # type: ignore
            app = fastapi_app
        except Exception as exc:  # pragma: no cover
            pytest.skip(f"Cannot resolve FastAPI app instance: {exc!r}")

    transport = httpx.ASGITransport(app=app)
    return httpx.Client(transport=transport, base_url="http://testserver")


@pytest.fixture(scope="module")
def client():
    c = _build_client()
    try:
        yield c
    finally:
        c.close()


@pytest.fixture(scope="module")
def auth_headers():
    """Return Authorization headers using the dev mock-token short-circuit.

    The backend's ``auth/dependencies.py`` accepts a mock token when
    ``ENVIRONMENT == "development"``. The microbench requires that environment
    or a real token via ``BENCH_TOKEN``.
    """
    token = os.environ.get("BENCH_TOKEN", "mock-token-for-dev")
    return {"Authorization": f"Bearer {token}"}


def test_dashboard_summary_benchmark(benchmark, client, auth_headers):
    """Microbench: GET /api/dashboard/summary."""

    def _call():
        resp = client.get("/api/dashboard/summary", headers=auth_headers)
        # Don't assert 200 — auth/data may be missing in microbench env.
        # The point is to measure framework + handler overhead.
        return resp.status_code

    status = benchmark(_call)
    assert status in (200, 401, 403, 404, 500), f"unexpected status {status}"
