# IW-1 — Test pyramid integration

## Summary
Relocated the audit-wave test pyramid from `audit/30-tests/` into canonical homes inside the main repo: `backend/tests/`, `frontend/tests/` (with `frontend/vitest.config.ts`), `ml-worker/tests/`, and `e2e/`. The bit-rotted internship backend test suite (BE-TEST-001..004) was deleted and replaced. No new tests were written and no behavior was changed; this is pure relocation plus path/import rewrites and a `pyproject.toml` merge for backend pytest config. The `audit/30-tests/` directory is intentionally left in place (now mostly empty subtrees + `node_modules`) for IW-6 to delete with the rest of `audit/`.

## Files moved
| Source | Destination | Notes |
|---|---|---|
| audit/30-tests/backend/conftest.py | backend/tests/conftest.py | replaces bit-rotted SQLite fixture; testcontainers Postgres+Redis |
| audit/30-tests/backend/factories/ | backend/tests/factories/ | factory-boy SQLAlchemy factories |
| audit/30-tests/backend/helpers/ | backend/tests/helpers/ | `auth_client.py`, `supabase_mock.py` |
| audit/30-tests/backend/integration/ | backend/tests/integration/ | router-level integration suite |
| audit/30-tests/backend/security/ | backend/tests/security/ | BE-SEC-* fix proofs |
| audit/30-tests/backend/concurrency/ | backend/tests/concurrency/ | BE-CONC-* race tests |
| audit/30-tests/backend/contract/ | backend/tests/contract/ | Plaid/Supabase wire-shape pins |
| audit/30-tests/backend/README.md | backend/tests/README.md | updated paths |
| audit/30-tests/frontend/services/ | frontend/tests/services/ | |
| audit/30-tests/frontend/hooks/ | frontend/tests/hooks/ | |
| audit/30-tests/frontend/stores/ | frontend/tests/stores/ | |
| audit/30-tests/frontend/components/ | frontend/tests/components/ | |
| audit/30-tests/frontend/utils/ | frontend/tests/utils/ | |
| audit/30-tests/frontend/msw/ | frontend/tests/msw/ | |
| audit/30-tests/frontend/helpers/ | frontend/tests/helpers/ | |
| audit/30-tests/frontend/setup.ts | frontend/tests/setup.ts | |
| audit/30-tests/frontend/tsconfig.json | frontend/tests/tsconfig.json | path alias rewritten to `../src/*` |
| audit/30-tests/frontend/vitest.config.ts | frontend/vitest.config.ts | alias and include glob updated |
| audit/30-tests/ml-worker/conftest.py | ml-worker/tests/conftest.py | |
| audit/30-tests/ml-worker/unit/ | ml-worker/tests/unit/ | |
| audit/30-tests/ml-worker/helpers/ | ml-worker/tests/helpers/ | |
| audit/30-tests/ml-worker/pyproject.toml | ml-worker/tests/pyproject.toml | local (no parent ml-worker pyproject exists yet) |
| audit/30-tests/ml-worker/README.md | ml-worker/tests/README.md | updated paths |
| audit/30-tests/ml-worker/ab_test_results/ | ml-worker/tests/ab_test_results/ | |
| audit/30-tests/e2e/package.json | e2e/package.json | |
| audit/30-tests/e2e/package-lock.json | e2e/package-lock.json | |
| audit/30-tests/e2e/playwright.config.ts | e2e/playwright.config.ts | |
| audit/30-tests/e2e/tsconfig.json | e2e/tsconfig.json | |
| audit/30-tests/e2e/fixtures/ | e2e/fixtures/ | |
| audit/30-tests/e2e/tests/ | e2e/tests/ | |
| audit/30-tests/e2e/README.md | e2e/README.md | updated path in install snippet |
| audit/30-tests/e2e/.gitignore | e2e/.gitignore | |

## Files deleted
- backend/tests/conftest.py (old) — bit-rotted SQLite fixture (BE-TEST-001..004)
- backend/tests/__init__.py (old) — no longer needed
- backend/tests/unit/ (old) — superseded by audit integration/security/concurrency/contract suites
- backend/tests/integration/ (old) — replaced by audit integration suite (Postgres testcontainer, real router stack)
- backend/tests/pyproject.toml — folded into `backend/pyproject.toml`

## Files edited (path rewrites only)
- backend/pyproject.toml — `[tool.pytest.ini_options]` rewritten: `testpaths = ["tests/integration", "tests/security", "tests/concurrency", "tests/contract"]`, added markers (`security`, `concurrency`, `contract`, `slow`), `asyncio_mode = "auto"`, dropped `--strict-config` and `error` filterwarnings (audit suite emits SQLA/pydantic deprecations).
- backend/tests/README.md — top heading + run snippet rewritten for canonical path.
- frontend/package.json — added `test:vitest`, `test:vitest:run`, `test:vitest:watch` scripts; added Vitest devDependencies (`vitest@^2.1.9`, `@vitest/ui@^2.1.9`, `happy-dom@^15.11.7`, `msw@^2.7.0`); existing Jest scripts and devDeps untouched.
- frontend/vitest.config.ts — `FRONTEND_SRC` resolved from `__dirname/src`; `setupFiles: ['./tests/setup.ts']`; `include: ['tests/**/*.{test,spec}.{ts,tsx}']`; exclude switched to `src/**`.
- frontend/tests/tsconfig.json — `paths` and `include` rewritten from `../../../frontend/src/*` to `../src/*`.
- ml-worker/tests/README.md — paths rewritten to canonical `ml-worker/tests/`.
- ml-worker/tests/pyproject.toml — description path rewrite.
- ml-worker/tests/unit/test_confidence_thresholds.py, test_confidence_buckets.py — comment path rewrites.
- e2e/README.md — install snippet path rewrite.

## Verification
- `python3 -m py_compile backend/tests/conftest.py` — exit 0, silent.
- `python3 -c "import tomllib; tomllib.loads(open('backend/pyproject.toml').read())"` — `backend pyproject OK`.
- `cd frontend && node -e "require('./package.json')"` — `package.json OK`.
- `cd e2e && npx tsc --noEmit -p tsconfig.json` — SKIPPED (`npm install` not run; node_modules absent). IW-2 / CI will install and re-check.
- `grep -rn "audit/30-tests\|audit\.30_tests" backend/tests frontend/tests frontend/vitest.config.ts ml-worker/tests e2e` — empty (text matches; binary `*.pyc` removed).

## Open follow-ups
- IW-2 will rewrite the CI workflow to point at `backend/tests/`, `frontend/tests/` (Vitest) + existing Jest, `ml-worker/tests/`, and `e2e/`.
- Backend integration tests require a running Docker daemon (testcontainers spins `postgres:15-alpine` + `redis:7-alpine`). Document this in the run-tests runbook.
- `ml-worker/` has no top-level `pyproject.toml`; the test suite keeps a local `ml-worker/tests/pyproject.toml`. If a parent `ml-worker/pyproject.toml` is introduced later, fold the `[tool.pytest.ini_options]` block in.
- IW-6 will delete the now-empty `audit/30-tests/` (and the rest of `audit/`).
