"""
Audit-wave backend test fixtures.

This conftest deliberately replaces `backend/tests/conftest.py` (which is
bit-rotted — see BE-TEST-001..004). The internship conftest is left in place;
this file lives in a separate venv and runs against real Postgres + Redis via
testcontainers, so JSONB / ARRAY / Postgres enums / `SET LOCAL` all work.

Key invariants:
- Environment variables that drive `app.config.Settings` are written BEFORE
  any `from app.* import` statement. FastAPI Settings reads env at import
  time; if we wait until inside a fixture, the app boots against whatever the
  developer's local `.env` happens to contain.
- Postgres + Redis containers are session-scoped (one per `pytest` invocation).
- Each test runs inside a SAVEPOINT that rolls back on exit, so test order
  doesn't matter and the schema is created exactly once.
- Supabase is stubbed via respx routed at `https://stub.supabase.co`; no test
  in this suite is allowed to talk to a live Supabase.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Generator, Iterator

import pytest

# ---------------------------------------------------------------------------
# 1. sys.path: expose `backend/app` without installing the app as a package.
#
# `pip install -e ../../../backend` is the recommended path (see README), but
# if the user forgets, falling back to a sys.path insertion lets the suite at
# least *attempt* to import. This is intentionally narrow — we add exactly one
# directory.
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND_DIR = _REPO_ROOT / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))


# ---------------------------------------------------------------------------
# 2. Containers: start Postgres + Redis BEFORE any `app.*` import.
#
# We do this at module import (not in a fixture) because `app.config.Settings`
# evaluates `os.getenv("DATABASE_URL", ...)` at class-body time. If we set the
# env vars from inside a `pytest_configure` hook, Settings has already been
# constructed against localhost.
# ---------------------------------------------------------------------------
def _bootstrap_containers() -> tuple:
    """Start Postgres + Redis testcontainers and write env vars.

    Returns the container instances so the session-scoped fixtures below can
    yield them and stop them at teardown.
    """
    # Imported lazily so `pytest --collect-only` without Docker still produces
    # a useful error message rather than failing during collection.
    from testcontainers.postgres import PostgresContainer
    from testcontainers.redis import RedisContainer

    pg = PostgresContainer("postgres:15-alpine")
    pg.start()

    rd = RedisContainer("redis:7-alpine")
    rd.start()

    # PostgresContainer returns a URL with the `postgresql+psycopg2://` driver
    # already baked in on recent versions; older versions return plain
    # `postgresql://`. Normalize to the driver our app expects.
    db_url = pg.get_connection_url()
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    redis_host = rd.get_container_host_ip()
    redis_port = rd.get_exposed_port(6379)
    redis_url = f"redis://{redis_host}:{redis_port}/0"

    os.environ["DATABASE_URL"] = db_url
    os.environ["REDIS_URL"] = redis_url
    os.environ["ENVIRONMENT"] = "test"
    os.environ["DEBUG"] = "true"
    # Settings.validate_required_settings() only enforces these in `production`,
    # but we set them anyway so the suite can flip ENVIRONMENT=production later
    # (see security/test_dev_bypass_disabled_in_prod.py).
    os.environ["SECRET_KEY"] = "test-secret-must-be-32-chars-long-xx"
    os.environ["SUPABASE_URL"] = "https://stub.supabase.co"
    os.environ["SUPABASE_ANON_KEY"] = "stub-anon-key"
    os.environ["SUPABASE_WEBHOOK_SECRET"] = "stub-webhook-secret"
    # Disable seeding/feature toggles that would make a HTTP call we don't mock.
    os.environ.setdefault("ENABLE_PLAID", "false")
    os.environ.setdefault("ENABLE_ML_WORKER", "false")

    return pg, rd


# Module-level bootstrap. If Docker is missing, this raises during collection
# with a clear `DockerException`, which is the correct failure mode.
_PG_CONTAINER, _REDIS_CONTAINER = _bootstrap_containers()


# ---------------------------------------------------------------------------
# 3. Now it's safe to import the app. Settings has been constructed against
#    the testcontainer URLs.
# ---------------------------------------------------------------------------
from app.main import app  # noqa: E402
from app.database import get_db  # noqa: E402
# IMPORTANT: there are two `Base` declarations in this codebase.
# `app.database.Base` is a legacy declarative_base() that is empty (no model
# inherits from it). The real one is `app.models.base.Base` (DeclarativeBase),
# which every actual model class extends. Use the real one for create_all.
from app.models.base import Base  # noqa: E402
import importlib as _importlib  # noqa: E402
_importlib.import_module("app.models")  # ensure all model modules register
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker, Session  # noqa: E402


# ---------------------------------------------------------------------------
# 4. Session-scoped fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def postgres_container():
    """Yield the running Postgres container (started at import time)."""
    yield _PG_CONTAINER
    _PG_CONTAINER.stop()


@pytest.fixture(scope="session")
def redis_container():
    """Yield the running Redis container (started at import time)."""
    yield _REDIS_CONTAINER
    _REDIS_CONTAINER.stop()


@pytest.fixture(scope="session")
def engine(postgres_container):
    """Build a SQLAlchemy engine pointed at the testcontainer Postgres.

    We deliberately do NOT reuse `app.database.engine` because that engine was
    constructed at import time and may have cached connection metadata. A
    fresh engine guarantees we see the schema we just created here.

    NOTE: Section D will switch this to running Alembic migrations instead of
    `Base.metadata.create_all`. For this foundation wave we use create_all so
    new tests aren't blocked on the migration backfill (BE-PR-001/002).
    """
    eng = create_engine(os.environ["DATABASE_URL"], future=True)
    Base.metadata.create_all(bind=eng)
    yield eng
    eng.dispose()


@pytest.fixture(scope="session")
def session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


# ---------------------------------------------------------------------------
# 5. Function-scoped DB session inside a SAVEPOINT.
#
# Pattern lifted from the SQLAlchemy docs ("Joining a Session into an external
# transaction"). The outer transaction is rolled back at teardown, so every
# test starts from the same empty DB without re-running create_all.
# ---------------------------------------------------------------------------
@pytest.fixture(scope="function")
def db_session(engine, session_factory) -> Iterator[Session]:
    connection = engine.connect()
    transaction = connection.begin()
    session = session_factory(bind=connection)

    # Bind a nested SAVEPOINT so service code that calls `session.commit()`
    # only commits to the savepoint, not the outer transaction.
    nested = connection.begin_nested()

    from sqlalchemy import event as _event

    @_event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, trans):  # pragma: no cover - SA hook
        nonlocal nested
        if trans.nested and not trans._parent.nested:
            nested = connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


# ---------------------------------------------------------------------------
# 6. Supabase mock — installed for every test via autouse so no test
#    accidentally hits the real Supabase (which would 401 against `stub-key`
#    and produce confusing failures).
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def supabase_mock():
    """Mount respx routes for stub Supabase auth endpoints.

    Tests that need to assert specific Supabase behaviour can import
    `helpers.supabase_mock.install_default_routes` and add their own routes on
    top of the returned `respx_mock` object.
    """
    from helpers.supabase_mock import install_default_routes
    import respx

    with respx.mock(assert_all_called=False) as router:
        install_default_routes(router)
        # Expose the active router so helpers (e.g. auth_client) can register
        # per-test routes on the SAME MockRouter that's actually intercepting
        # httpx traffic. Plain `respx.get(...)` registers on the global mock,
        # which is a different router and never gets consulted.
        from helpers import supabase_mock as _sb
        _sb._ACTIVE_ROUTER = router
        try:
            yield router
        finally:
            _sb._ACTIVE_ROUTER = None


# ---------------------------------------------------------------------------
# 7. App client with `get_db` overridden to use our SAVEPOINT session.
# ---------------------------------------------------------------------------
@pytest.fixture(scope="function")
def app_client(db_session):
    from fastapi.testclient import TestClient

    def _override_get_db():
        try:
            yield db_session
        finally:
            # Don't close — the db_session fixture handles teardown.
            pass

    app.dependency_overrides[get_db] = _override_get_db
    # `get_db_with_user_context` depends on `get_db`, so override is inherited.

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# 8. Make factories see the per-test session.
#
# factory-boy needs `sqlalchemy_session` set before `.create()` is called. We
# do that here so individual tests can just call `UserFactory.create()`.
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _bind_factories_to_session(db_session):
    from factories import bind_session, unbind_session

    bind_session(db_session)
    yield
    unbind_session()
