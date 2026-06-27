# Backend Performance Benchmarking Harness

Foundation-wave scaffolding for perf testing the `finance-tracker` FastAPI backend.
This harness is intentionally additive: it lives entirely under `benchmarks/backend/`
and never modifies internship code. It targets a **running** stack — it does not start
services itself.

Targets the BE-PERF-001..008 findings in `docs/audit/findings.csv`.

## Layout

```
benchmarks/backend/
├── pyproject.toml            # pinned deps: locust, requests, httpx, pytest, pytest-benchmark
├── README.md                 # this file
├── locust/
│   ├── locustfile.py         # 3 user classes; per-endpoint p50/p95/p99 CSV
│   ├── tasks/                # auth / dashboard / transactions / ml task sets
│   └── data/seed_users.json  # fixture for benchmark users (populated by scripts/seed_bench_users.py)
├── microbench/
│   └── test_dashboard_summary_bench.py   # pytest-benchmark; opt-in via BENCH_RUN=1
├── scripts/
│   ├── capture_baseline.sh   # 60s headless locust run; writes reports/<git-sha>/
│   └── seed_bench_users.py   # creates N bench users via /api/auth/register
└── reports/                  # output (gitkept)
```

## Setup

```bash
cd benchmarks/backend
python -m venv .venv
.venv/bin/pip install -e .
```

## Running locust

The stack must already be up (`docker compose up` from repo root). Default host is
`http://localhost:8000`; override with `BENCH_HOST`.

Smoke (import-only check, does not require stack):

```bash
.venv/bin/python -c "from locust.locustfile import *; print('ok')"
```

Interactive (web UI on http://localhost:8089):

```bash
.venv/bin/locust -f locust/locustfile.py
```

Headless 60s, 50 users, ramp 5/s:

```bash
BENCH_HOST=http://localhost:8000 \
  .venv/bin/locust -f locust/locustfile.py --headless \
  -u 50 -r 5 -t 60s \
  --csv reports/local --html reports/local.html
```

User classes (mix via `--class-picker` or per-class flags):

- `AuthOnlyUser` — login + `/api/auth/me`. Baseline.
- `DashboardUser` — login then weighted mix over `/api/dashboard/summary`,
  `/api/dashboard/category-breakdown`, `/api/dashboard/net-worth-trend`.
- `TransactionUser` — login then weighted mix over `GET /api/transactions`
  (paginated), `POST /api/transactions`, `DELETE /api/transactions/{id}`.

A separate `MLCategorizeUser` exists in `tasks/ml.py` (commented-in optionally) for
the BE-PERF-001 hotspot; it is **not** included in the default `locustfile.py` user
mix because it depends on a running ML worker and Celery broker. Enable with
`BENCH_INCLUDE_ML=1`.

### Custom percentile CSV

The locustfile registers an `events.request.add_listener` that streams every request
sample into `reports/requests_raw.csv` and emits a per-endpoint
`reports/percentiles.csv` (p50/p95/p99/avg/count) on quit. Standard locust
`--csv reports/local` output is also written.

## Capturing a baseline

```bash
BENCH_HOST=http://localhost:8000 BENCH_USERS=50 BENCH_RAMP=5 BENCH_DURATION=60s \
  bash scripts/capture_baseline.sh
```

Output goes to `reports/<git-sha>/` containing:

- `locust_stats.csv`, `locust_stats_history.csv`, `locust_failures.csv`
- `locust.html`
- `percentiles.csv` (custom)
- `meta.json` (sha, host, user count, duration, timestamp)

## Seeding benchmark users

`locust/data/seed_users.json` is a placeholder. Populate before a real run:

```bash
.venv/bin/python scripts/seed_bench_users.py \
  --count 50 \
  --host http://localhost:8000 \
  --out locust/data/seed_users.json
```

This script requires a clean DB (or unique email prefixes); it documents but does
not enforce DB hygiene. See script header comments.

## Microbenchmarks

Microbench is in-process via FastAPI `TestClient`/`httpx.ASGITransport` against the
backend app. It is **off by default**; opt in with the env var:

```bash
BENCH_RUN=1 .venv/bin/pytest -m benchmark
```

It will skip cleanly if the backend package cannot be imported (e.g. running this
folder on a machine without backend deps installed).

## Success metrics tracked

From `docs/audit/improvement-sections/A-performance.md`:

- `p95 /api/dashboard/summary < 200 ms @ 50 RPS`
- `p99 /api/ml/categorize < 500 ms` (delegated to Section F; harness still measures)

The `percentiles.csv` produced by every run includes both endpoints when exercised.

## Caveats / known limits (foundation wave)

- Not wired into CI yet; no perf regression gate. That belongs to a later wave.
- Seed script uses public `/api/auth/register` and Supabase confirmation flow;
  for fully isolated runs use a Supabase project in dev mode or seed via
  `scripts/seed_data.py` against a local DB.
- ML user class assumes ml-worker + Celery broker are reachable; otherwise
  failures will dominate the run.
