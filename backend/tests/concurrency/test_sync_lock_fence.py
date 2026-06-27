"""BE-CONC-002 — Sync lock has no fence token.

`backend/app/services/transaction_sync_service.py:55-91` acquires a Redis
sync lock with a value of `worker-<task-name>`, but `_release_sync_lock`
just calls `DEL` on the key — without checking whether the caller actually
holds the lock. Any worker can stomp another worker's lock (classic Martin
Kleppmann "fence token" problem).

Hardened behaviour:

- Each acquirer should mint a UUID fence token, stash it as the lock value,
  and `_release_sync_lock(token)` should perform a Lua-CAS-DELETE that only
  removes the key if the value matches the token.

This test simulates worker A acquiring the lock for an account, then worker
B (a different asyncio task) attempting to release it. Worker B's release
must fail (return False / no-op), and the lock must remain held until A
releases it with its own token.

xfail strict=False until the fence-token contract is implemented.
"""

from __future__ import annotations

import asyncio

import pytest

from app.services.transaction_sync_service import TransactionSyncService


@pytest.mark.concurrency
def test_release_with_wrong_or_missing_fence_is_rejected(redis_container):
    """Worker B must NOT be able to release worker A's lock."""

    account_id = "acc-fence-test-123"

    async def _scenario():
        svc = TransactionSyncService()

        # Worker A acquires the lock (named asyncio task so the lock value
        # encodes "worker A").
        async def worker_a_acquire():
            return await svc._acquire_sync_lock(account_id)

        task_a = asyncio.create_task(worker_a_acquire(), name="worker-A")
        acquired_a = await task_a
        # Hardened API now returns the fence token (truthy str) on success
        # and None on failure. Either truthy result is acceptable for the
        # precondition.
        assert acquired_a, "precondition: worker A must acquire"
        token_a = acquired_a if isinstance(acquired_a, str) else None

        # Worker B (a different task) tries to release. With the current
        # implementation `_release_sync_lock` blindly DELETEs the key, so it
        # returns True — that's the bug. With a fence token, B has no token
        # (or a wrong token) and the release must be rejected.
        async def worker_b_release():
            # Hardened API SHOULD accept a fence_token kwarg; today it doesn't.
            # We call with no token; the test asserts B can't release A's lock.
            try:
                return await svc._release_sync_lock(account_id, fence_token="WRONG")  # type: ignore[call-arg]
            except TypeError:
                # Current signature accepts no token at all — that itself is
                # the BE-CONC-002 finding. Fall back to the bare call.
                return await svc._release_sync_lock(account_id)

        task_b = asyncio.create_task(worker_b_release(), name="worker-B")
        released_by_b = await task_b
        # Hardened API returns False (or any falsy) when the token is wrong
        # or missing; we accept any falsy value here.
        assert not released_by_b, (
            "BE-CONC-002 regression: worker B was able to release worker A's "
            "lock with a wrong/missing fence token."
        )

        # Sanity: the lock should still be held — a second attempt to acquire
        # by yet another worker must fail.
        async def worker_c_acquire():
            return await svc._acquire_sync_lock(account_id)

        task_c = asyncio.create_task(worker_c_acquire(), name="worker-C")
        acquired_c = await task_c
        # Hardened API returns None (falsy) when the lock is held; the bool
        # `False` is a legacy return value. Accept any falsy.
        assert not acquired_c, (
            "BE-CONC-002 regression: lock was effectively released by B "
            "(worker C just acquired it)."
        )

        # Cleanup as worker A.
        async def cleanup_a():
            try:
                return await svc._release_sync_lock(account_id, fence_token="A")  # type: ignore[call-arg]
            except TypeError:
                return await svc._release_sync_lock(account_id)

        await asyncio.create_task(cleanup_a(), name="worker-A")

    asyncio.run(_scenario())
