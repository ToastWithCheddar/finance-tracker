"""Seed N benchmark users via /api/auth/register and write a credentials JSON.

Usage::

    python scripts/seed_bench_users.py --count 50 \
        --host http://localhost:8000 \
        --out locust/data/seed_users.json

This is a **placeholder-quality** seed script for the foundation wave:

- It POSTs ``/api/auth/register`` for each user, which delegates to Supabase.
  In a real Supabase project this typically requires email confirmation;
  for benchmarking, configure your dev Supabase instance with auto-confirm
  enabled, OR run the backend in ``ENVIRONMENT=development`` mode and use
  the dev mock-token short-circuit for auth (see backend ``auth/dependencies.py``).
- It does NOT clean up. Re-running with the same prefix will see 409 collisions;
  pass ``--prefix`` for a fresh batch or wipe the DB between runs.
- It does NOT seed transactions/categories. Real perf runs need data; use
  ``backend/scripts/seed_data.py`` against a clean DB for that.

The output JSON shape is::

    [{"email": "...", "password": "..."}, ...]

which ``locust/tasks/auth.py`` consumes.
"""
from __future__ import annotations

import argparse
import json
import secrets
import sys
import uuid
from pathlib import Path

import requests


def _make_password() -> str:
    return "Bench!" + secrets.token_urlsafe(12)


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed bench users.")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--host", default="http://localhost:8000")
    parser.add_argument("--prefix", default=None, help="Email local-part prefix (default: random).")
    parser.add_argument("--domain", default="bench.invalid")
    parser.add_argument(
        "--out",
        default=str(Path(__file__).resolve().parent.parent / "locust" / "data" / "seed_users.json"),
    )
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    prefix = args.prefix or f"bench-{uuid.uuid4().hex[:8]}"
    register_url = f"{args.host.rstrip('/')}/api/auth/register"
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    created: list[dict] = []
    for i in range(args.count):
        email = f"{prefix}-{i:04d}@{args.domain}"
        password = _make_password()
        body = {"email": email, "password": password, "full_name": f"Bench User {i}"}
        try:
            resp = requests.post(register_url, json=body, timeout=args.timeout)
        except requests.RequestException as exc:
            print(f"[seed] {email}: network error: {exc}", file=sys.stderr)
            continue
        if resp.status_code in (200, 201):
            created.append({"email": email, "password": password})
            print(f"[seed] {email}: ok")
        elif resp.status_code in (409, 422):
            # Treat conflicts as "user already exists"; keep credentials so
            # subsequent runs still have a working set.
            created.append({"email": email, "password": password})
            print(f"[seed] {email}: already exists (status={resp.status_code})")
        else:
            print(
                f"[seed] {email}: failed status={resp.status_code} body={resp.text[:200]!r}",
                file=sys.stderr,
            )

    out_path.write_text(json.dumps(created, indent=2) + "\n")
    print(f"[seed] wrote {len(created)} credentials to {out_path}")
    return 0 if created else 1


if __name__ == "__main__":
    raise SystemExit(main())
