"""Auth tasks: login + token cache + /me.

The token cache lives on the Locust user instance so each simulated user
logs in once and reuses its access token for the lifetime of the run.
Refresh is exercised periodically.
"""
from __future__ import annotations

import json
import os
import random
from pathlib import Path
from typing import Optional

from locust import task, TaskSet


_SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "seed_users.json"


def _load_seed_users() -> list[dict]:
    if not _SEED_PATH.exists():
        return []
    try:
        data = json.loads(_SEED_PATH.read_text())
        if isinstance(data, list):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return []


_SEED_USERS = _load_seed_users()


def pick_credentials() -> tuple[str, str]:
    """Return (email, password) for one bench user, or fall back to env defaults.

    Fallback values are intentionally invalid against a real backend so that
    misconfigured runs fail loudly rather than silently authenticating as a
    real account.
    """
    if _SEED_USERS:
        u = random.choice(_SEED_USERS)
        return u["email"], u["password"]
    return (
        os.environ.get("BENCH_DEFAULT_EMAIL", "bench-user@example.invalid"),
        os.environ.get("BENCH_DEFAULT_PASSWORD", "bench-password-please-seed"),
    )


def login(client, email: Optional[str] = None, password: Optional[str] = None) -> Optional[str]:
    """POST /api/auth/login. Returns access_token or None on failure."""
    if email is None or password is None:
        email, password = pick_credentials()
    with client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
        name="POST /api/auth/login",
        catch_response=True,
    ) as resp:
        if resp.status_code != 200:
            resp.failure(f"login status={resp.status_code}")
            return None
        try:
            body = resp.json()
        except ValueError:
            resp.failure("login: non-JSON body")
            return None
        token = body.get("access_token") or body.get("session", {}).get("access_token")
        if not token:
            resp.failure("login: no access_token in body")
            return None
        return token


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class AuthTaskSet(TaskSet):
    """Minimal auth-only flow: login already happened on_start; just call /me."""

    @task(5)
    def me(self):
        token = getattr(self.user, "token", None)
        if not token:
            return
        self.client.get(
            "/api/auth/me",
            headers=auth_headers(token),
            name="GET /api/auth/me",
        )

    @task(1)
    def refresh(self):
        token = getattr(self.user, "token", None)
        if not token:
            return
        # Backend refresh endpoint expects the refresh token; we don't always
        # have one in the foundation harness. Treat missing refresh tokens as
        # a skip (don't count as failure).
        refresh_tok = getattr(self.user, "refresh_token", None)
        if not refresh_tok:
            return
        self.client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_tok},
            headers=auth_headers(token),
            name="POST /api/auth/refresh",
        )
