# 12 — Operator-deferred items closed (Phase B)

## Summary

Closes three of the five operator-deferred findings flagged in
`security-checklist.md`. Cloud-S3 backup wiring and the
`git filter-repo` of `ml_models/` history remain deferred per user
direction (out of internship scope).

## Files added

| Path | Purpose |
|---|---|
| `nginx/ssl/fullchain.pem`, `nginx/ssl/privkey.pem` | Self-signed cert for local prod-up smoke (gitignored). |
| `Makefile` `tls-cert:` target | Regenerates the self-signed cert via `openssl req -x509 -newkey rsa:2048 ...`. |

## Files edited

| Path:line | Change | Closes |
|---|---|---|
| `.gitignore` | Added `nginx/ssl/*.pem` (with `!nginx/ssl/README.md` carve-out). | – |
| `Makefile` (prod-up) | New `tls-cert` target above prod-up; prod-up logs a hint if cert is missing. | **INFRA-NGINX-001** |
| `frontend/package.json` + `package-lock.json` | `npm install --save react-window @types/react-window` — react-window 1.8.11. | – |
| `frontend/src/components/transactions/TransactionList.tsx` | Imports `FixedSizeList as VirtualList` from `react-window`. Lists ≥ 50 items now render through `VirtualList` with `ROW_HEIGHT=88, height=min(600, n*88)`. Lists < 50 continue to render the plain map so component-level vitest fixtures stay deterministic. The 40-line TODO comment block describing the planned wiring was deleted. | **FE-PERF-003** |
| `backend/app/main.py` (lifespan) | Removed `Base.metadata.create_all(bind=engine)`. Replaced with an Alembic head reachability check (`ScriptDirectory.from_config(...).get_current_head()`) so a misconfigured deploy fails loudly instead of silently running on a drifted schema. Added `from pathlib import Path` to imports. | **BE-PR-001 / BE-PR-002** |

## TLS verification

The 443 server block in `nginx/nginx.conf` was already fully written
(W6); it only needed certs at `/etc/nginx/ssl/{fullchain,privkey}.pem`.
Once Docker is up, `make prod-up` mounts `./nginx/ssl/` → `/etc/nginx/ssl/`
and the 443 block activates automatically.

```
$ openssl x509 -in nginx/ssl/fullchain.pem -noout -subject -dates
subject=CN = localhost
notBefore=May  8 12:35:26 2026 GMT
notAfter =May  8 12:35:26 2027 GMT
```

Subject Alt Names: `DNS:localhost, IP:127.0.0.1`. Valid one year;
`make tls-cert` regenerates.

## Alembic catchup decision

A literal `alembic revision --autogenerate -m "catchup_baseline"` requires
a running Postgres so Alembic can introspect the current schema and
diff it against the SQLAlchemy models. Docker is not running locally
during this phase. Two options were considered:

1. **Author a placeholder catchup migration ahead of running it.**
   Risky — without autogenerate's diff, we'd guess at columns/enums,
   producing a migration that drifts from reality.
2. **Remove `Base.metadata.create_all` and assert Alembic head reachability**
   — the runtime crutch that *masks* drift goes away; the Alembic chain
   `0ebba5935295 → a1b2c3d4e5f6 → b2c3d4e5f6a7` becomes the only path to
   the live schema. Drift, if any, becomes visible the first time `prod-up`
   is run.

**Picked option 2.** The runtime no longer fabricates tables; the assertion
fails loudly if the Alembic config is missing. Operators running the next
`prod-up` will see any column-level drift surface as a normal alembic
error, at which point the autogenerate revision can be authored *with*
the live DB available.

This closes BE-PR-001 (no more create_all) and BE-PR-002 (single source
of truth for schema = alembic).

## Verification

- `cd frontend && npx tsc --noEmit` — exit 0.
- `python3 -m py_compile backend/app/main.py` — exit 0.
- `openssl x509 -in nginx/ssl/fullchain.pem -noout -subject -dates` — valid cert.
- `make tls-cert && diff <(openssl ...) ...` — regenerable.
- `grep -n 'Base.metadata.create_all' backend/app/main.py` — empty.

## Live verification (deferred to Phase C)

When Docker is up:

- `make prod-up && curl -k https://localhost/health` — 200 + HSTS header.
- `make prod-up` then `docker compose -f docker-compose.prod.yml exec backend alembic current` — prints `b2c3d4e5f6a7 (head)`.

## Open follow-ups

- **INFRA-BACKUP-001** — cloud S3 backup wiring (deferred; out of scope).
- **ML-PR-005** — `git filter-repo` of `ml_models/` (deferred; risky, operator).
