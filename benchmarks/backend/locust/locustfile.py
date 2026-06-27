"""Locust entrypoint for finance-tracker backend benchmarks.

Run with::

    locust -f locust/locustfile.py

Default host comes from env var ``BENCH_HOST`` (defaults to
``http://localhost:8000``). The stack must already be running.

User classes:

- ``AuthOnlyUser`` — login + ``/me`` baseline.
- ``DashboardUser`` — login then weighted dashboard mix.
- ``TransactionUser`` — login then weighted transactions CRUD.
- ``MLCategorizeUser`` — opt-in via ``BENCH_INCLUDE_ML=1``.

Outputs (in addition to Locust's own ``--csv``):

- ``reports/requests_raw.csv`` — every request sample.
- ``reports/percentiles.csv`` — per-endpoint p50/p95/p99/avg/count, written on quit.
"""
from __future__ import annotations

import csv
import os
import sys
import threading
import time
from collections import defaultdict
from pathlib import Path

# Make sibling ``tasks`` package importable when locust loads this file by path.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from locust import HttpUser, between, events  # noqa: E402

from tasks.auth import AuthTaskSet, login  # noqa: E402
from tasks.dashboard import DashboardTaskSet  # noqa: E402
from tasks.transactions import TransactionTaskSet  # noqa: E402
from tasks.ml import MLTaskSet  # noqa: E402


# ---------------------------------------------------------------------------
# Per-endpoint sample collection -> percentiles CSV on quit
# ---------------------------------------------------------------------------

_REPORTS_DIR = Path(os.environ.get("BENCH_REPORTS_DIR", _HERE.parent / "reports"))
_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

_samples_lock = threading.Lock()
_samples: dict[str, list[float]] = defaultdict(list)
_raw_csv_path = _REPORTS_DIR / "requests_raw.csv"
_percentiles_csv_path = _REPORTS_DIR / "percentiles.csv"

# Stream raw samples so a crash mid-run still leaves data behind.
_raw_fh = _raw_csv_path.open("w", newline="")
_raw_writer = csv.writer(_raw_fh)
_raw_writer.writerow(["timestamp", "request_type", "name", "response_time_ms", "status"])


@events.request.add_listener
def _on_request(
    request_type,
    name,
    response_time,
    response_length,
    exception,
    context,
    **kwargs,
):
    status = "fail" if exception is not None else "ok"
    key = f"{request_type} {name}"
    with _samples_lock:
        if exception is None:
            _samples[key].append(float(response_time))
        try:
            _raw_writer.writerow([f"{time.time():.3f}", request_type, name, f"{response_time:.2f}", status])
        except Exception:
            pass


def _percentile(sorted_samples: list[float], pct: float) -> float:
    if not sorted_samples:
        return 0.0
    if len(sorted_samples) == 1:
        return sorted_samples[0]
    # Nearest-rank, clamped.
    k = max(0, min(len(sorted_samples) - 1, int(round((pct / 100.0) * (len(sorted_samples) - 1)))))
    return sorted_samples[k]


@events.quitting.add_listener
def _on_quit(environment, **kwargs):
    try:
        _raw_fh.flush()
        _raw_fh.close()
    except Exception:
        pass
    rows = []
    with _samples_lock:
        for key, samples in _samples.items():
            samples_sorted = sorted(samples)
            count = len(samples_sorted)
            if count == 0:
                continue
            avg = sum(samples_sorted) / count
            rows.append({
                "endpoint": key,
                "count": count,
                "avg_ms": round(avg, 2),
                "p50_ms": round(_percentile(samples_sorted, 50), 2),
                "p95_ms": round(_percentile(samples_sorted, 95), 2),
                "p99_ms": round(_percentile(samples_sorted, 99), 2),
                "max_ms": round(samples_sorted[-1], 2),
            })
    rows.sort(key=lambda r: r["endpoint"])
    with _percentiles_csv_path.open("w", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["endpoint", "count", "avg_ms", "p50_ms", "p95_ms", "p99_ms", "max_ms"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


# ---------------------------------------------------------------------------
# User classes
# ---------------------------------------------------------------------------

_DEFAULT_HOST = os.environ.get("BENCH_HOST", "http://localhost:8000")


class _BaseUser(HttpUser):
    """Shared bootstrap: login once on start, cache token on the user instance."""

    abstract = True
    host = _DEFAULT_HOST
    wait_time = between(0.5, 2.0)

    def on_start(self):
        self.token = None
        self.refresh_token = None
        self.created_transaction_ids: list[str] = []
        token = login(self.client)
        if token:
            self.token = token


class AuthOnlyUser(_BaseUser):
    """Login + /me baseline; lightest possible auth-path user."""
    weight = 1
    tasks = [AuthTaskSet]


class DashboardUser(_BaseUser):
    """Heavier weight: dashboard endpoints are the main p95 target."""
    weight = 3
    tasks = [DashboardTaskSet]


class TransactionUser(_BaseUser):
    """CRUD-mix user; exercises sync DB hot path."""
    weight = 2
    tasks = [TransactionTaskSet]


# ML user is opt-in: requires ml-worker + Celery broker.
if os.environ.get("BENCH_INCLUDE_ML", "0") == "1":

    class MLCategorizeUser(_BaseUser):  # pragma: no cover - opt-in
        weight = 1
        tasks = [MLTaskSet]
