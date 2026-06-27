# 13a — Backend Fixture Triage Pass

Single-pass triage of the 21 failing tests in the audit-wave backend pytest
suite. Scope was strictly fixture/test surface — no edits under `backend/app/`.

## Result

| Metric                | Before | After |
| --------------------- | -----: | ----: |
| Passed                |     23 |    40 |
| Failed                |     21 |     0 |
| xfailed (known bugs)  |      6 |    10 |
| xpassed               |      8 |     8 |

Net: **+17 passing, 0 still red**, 4 newly-xfailed tests pinning real
app-code bugs (BE-AUTH-001, BE-HEALTH-001, BE-RECON-001 ×2).

## Root causes (the two big ones)

1. **Two MockRouter instances.** The autouse `supabase_mock` fixture in
   `tests/conftest.py` creates a local-state respx MockRouter via
   `with respx.mock(assert_all_called=False) as router`. Several tests and the
   `helpers.auth_client.make_authenticated_client` helper called module-level
   `respx.get(...)`, which writes to a *different* MockRouter (the global
   one). The local router is the one that actually intercepts in-flight httpx
   traffic, so per-test route overrides were silently ignored — every request
   resolved against the default user payload.
   - **Fix:** `supabase_mock` now stashes its router at
     `helpers.supabase_mock._ACTIVE_ROUTER`. The auth helper picks it up; the
     few tests that registered routes inline switched to taking
     `supabase_mock` as a fixture arg and calling `supabase_mock.get(...)`.

2. **Schema/test drift.** Several tests were written against an older
   contract:
   - `UserUpdate` no longer accepts `first_name`/`last_name` (only
     `display_name` and friends). Test assertions on `first_name` after PUT
     were guaranteed-fail.
   - `TransactionListResponse` exposes `transactions`, not `items`.
   - `goal_type`/`priority`/`status` enums are uppercase (SAVINGS/HIGH/ACTIVE),
     but the test sent lowercase.

## Per-test triage

| Test                                                                                                  | Category    | Action                                                                                                                                                          |
| ----------------------------------------------------------------------------------------------------- | ----------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tests/integration/test_users_router.py::test_get_me`                                                 | fixture-bug | Auth helper registered routes on global respx, not active router. Fixed conftest to expose router; helper now uses `_ACTIVE_ROUTER`.                            |
| `tests/integration/test_users_router.py::test_update_me_profile`                                      | fixture-bug | Test sent `first_name`/`last_name` which aren't in `UserUpdate` schema. Switched to `display_name`/`timezone`.                                                  |
| `tests/integration/test_accounts_router.py::test_list_accounts`                                       | fixture-bug | Fixed by the respx routing fix (no per-test edit needed).                                                                                                       |
| `tests/integration/test_accounts_router.py::test_update_account_rename`                               | fixture-bug | Same — auto-passes once auth resolves to the factory user.                                                                                                      |
| `tests/integration/test_categories_router.py::test_create_duplicate_category_rejected`                | fixture-bug | Same — auto-passes after respx fix.                                                                                                                             |
| `tests/integration/test_categories_router.py::test_my_categories`                                     | fixture-bug | Same.                                                                                                                                                           |
| `tests/integration/test_notifications_router.py::test_notifications_list_and_stats`                   | fixture-bug | Same.                                                                                                                                                           |
| `tests/integration/test_notifications_router.py::test_notification_mark_single_read`                  | fixture-bug | Same.                                                                                                                                                           |
| `tests/integration/test_notifications_router.py::test_notification_mark_all_read`                     | fixture-bug | Same.                                                                                                                                                           |
| `tests/integration/test_goals_router.py::test_goal_crud_and_stats`                                    | fixture-bug | Test sent lowercase enum values; schema requires uppercase. Updated payload.                                                                                    |
| `tests/integration/test_transactions_router.py::test_create_and_list_transaction`                     | fixture-bug | Test asserted `items` key; `TransactionListResponse` returns `transactions`. Made the assertion accept both.                                                    |
| `tests/security/test_rls_cross_user_leak.py::test_user_a_cannot_see_user_b_transactions`              | fixture-bug | Same `items` vs `transactions` mismatch. Fixed extraction.                                                                                                       |
| `tests/contract/test_supabase_get_user.py::test_supabase_get_user_response_extracts_id_and_email`     | fixture-bug | Used module-level `respx.get(...)` for override. Switched to `supabase_mock.get(...)`.                                                                          |
| `tests/concurrency/test_user_provisioning_toctou.py::test_concurrent_first_login_creates_exactly_one_user` | fixture-bug | Same module-level respx issue. Switched to active router.                                                                                                        |
| `tests/concurrency/test_sync_lock_fence.py::test_release_with_wrong_or_missing_fence_is_rejected`     | fixture-bug | `_acquire_sync_lock` now returns the fence token (`Optional[str]`), not a bool. Test asserted `is True`/`is False`; relaxed to truthiness.                       |
| `tests/security/test_dev_bypass_disabled_in_prod.py::test_dev_mock_token_rejected_when_environment_is_production` | fixture-bug | The dev bypass IS gated correctly, but the test fell through to Supabase, which the default mock happily accepted (200). Test now forces the mock to 401.       |
| `tests/security/test_dev_bypass_disabled_in_prod.py::test_dev_mock_token_rejected_when_environment_is_staging`    | fixture-bug | Same.                                                                                                                                                            |
| `tests/integration/test_auth_router.py::test_register_login_me_refresh_logout`                        | app-bug     | xfail BE-AUTH-001 — `UserCreate` schema omits `supabase_user_id`, so the field is silently dropped during register and the local row ends up with NULL.        |
| `tests/integration/test_health.py::test_health_detailed_includes_db_and_redis`                       | app-bug     | xfail BE-HEALTH-001 — health route calls `redis_client.ping()` but `RedisClient` has no `ping` method.                                                          |
| `tests/integration/test_reconciliation_router.py::test_reconcile_account_happy_path`                  | app-bug     | xfail BE-RECON-001 — route uses `EventType.ACCOUNT_RECONCILED` which is not defined on the `EventType` enum.                                                    |
| `tests/integration/test_reconciliation_router.py::test_reconcile_all_accounts`                        | app-bug     | xfail BE-RECON-001 — same EventType issue on the all-accounts variant.                                                                                          |

## Findings added to `docs/audit/findings.csv`

- **BE-AUTH-001** (P1, Security) — `UserCreate` schema omits `supabase_user_id`; `_create_local_user` silently drops it during registration.
- **BE-HEALTH-001** (P2, Production-readiness) — `RedisClient` exposes no `ping()`; `health.py` always reports redis unhealthy in detailed mode.
- **BE-RECON-001** (P1, Production-readiness) — `accounts_reconciliation.py` references undefined `EventType.ACCOUNT_RECONCILED`; every reconcile call 502s.

## Files touched

- `backend/tests/conftest.py` — stash active MockRouter at `helpers.supabase_mock._ACTIVE_ROUTER`.
- `backend/tests/helpers/supabase_mock.py` — declare `_ACTIVE_ROUTER` module global.
- `backend/tests/helpers/auth_client.py` — register per-user route on the active router.
- `backend/tests/integration/test_users_router.py` — drop unsupported `first_name`/`last_name` fields from PUT body.
- `backend/tests/integration/test_goals_router.py` — uppercase enum values.
- `backend/tests/integration/test_transactions_router.py` — accept `transactions` key in list response.
- `backend/tests/integration/test_health.py` — xfail BE-HEALTH-001.
- `backend/tests/integration/test_auth_router.py` — switch to `supabase_mock` fixture; xfail BE-AUTH-001.
- `backend/tests/integration/test_reconciliation_router.py` — xfail BE-RECON-001 ×2.
- `backend/tests/contract/test_supabase_get_user.py` — switch to active router.
- `backend/tests/concurrency/test_user_provisioning_toctou.py` — switch to active router.
- `backend/tests/concurrency/test_sync_lock_fence.py` — relax bool checks to truthiness (token return value).
- `backend/tests/security/test_dev_bypass_disabled_in_prod.py` — force supabase mock to 401 to isolate bypass semantics.
- `backend/tests/security/test_rls_cross_user_leak.py` — accept `transactions` key in list response.
- `docs/audit/findings.csv` — appended BE-AUTH-001, BE-HEALTH-001, BE-RECON-001.

## How to repro

```bash
cd backend && .venv/bin/pytest tests/ -q --tb=line
```

Final line should read:

```
40 passed, 10 xfailed, 8 xpassed, 12 warnings in ~17s
```
