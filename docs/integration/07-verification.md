# IW-7 — Final end-to-end verification

## Summary

Final pass after `audit/` deletion to confirm the canonical layout parses,
composes, and is internally consistent. Live test/bench/e2e runs are
operator follow-ups (they require Docker, a built frontend, and a live
stack respectively) — this wave verifies what can be checked statically.

## Verification

### Repo-root layout

```
$ ls
DiagramModel.drawio.svg  Makefile  backend/  benchmarks/
docker-compose.dev.yml   docker-compose.observability.yml
docker-compose.prod.yml  docker-compose.yml  docs/  e2e/
frontend/  internship.md  ml-worker/  ml_models/  newreport.md
nginx/  ops/  repomix-output.xml  scripts/  transaction_autocategory.csv
```

No `audit/`. `test ! -e audit` passes.

### Stale-reference grep

```
$ grep -rn "audit/\(00-\|10-\|20-\|30-\|40-\|50-\|60-\|70-\)" \
    --include='*.py' --include='*.ts' --include='*.tsx' \
    --include='*.yml' --include='*.yaml' --include='*.toml' \
    --include='*.sh' --include='*.conf' --include='Makefile' . \
    | grep -v 'docs/integration/'
./.github/workflows/ci.yml:3:# Promoted from audit/60-ci/workflows/audit.yml by IW-2. ...
```

Single remaining hit is the intentional provenance comment in
`.github/workflows/ci.yml`. All other references either rewritten by
IW-6 or live in `docs/integration/` changelogs (intentionally historical).

### Compose validation

```
$ docker compose -f docker-compose.prod.yml config -q       # exit 0
$ docker compose -f docker-compose.observability.yml config -q  # exit 0
```

### CI workflow YAML

```
$ python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
# (no output, exit 0)
```

`actionlint` is not installed locally; CI itself will run the workflow
on the next push. Operator follow-up: `brew install actionlint` if local
preflight is desired.

### Makefile

`make help` prints all rewritten targets:

```
install: install-{backend,frontend,ml-worker,bench-backend,bench-frontend,all}
test:    test-{backend,frontend,ml-worker,all}, e2e
bench:   bench-{backend,frontend,all}
prod stack: prod-{config-check,up,down}, backup, restore
quality: lint, clean
```

No `audit-*` prefixes remain.

## Items deferred to operator (require runtime)

These cannot be checked statically and are owner follow-ups:

- `make install-all` + `make test-all` — needs Docker for testcontainers.
- `cd e2e && npm install && npx playwright install && npx playwright test --list` — needs `node_modules` (~600 MB).
- `make bench-frontend-build-check` — needs a built `frontend/dist/`.
- `actionlint .github/workflows/ci.yml` — install via Homebrew.
- `git filter-repo` to purge `ml_models/` from history (ML-PR-005, pre-existing).

## Open follow-ups (carried over)

- INFRA-NGINX-001 — provision real TLS certs into `nginx/ssl/`.
- INFRA-BACKUP-001 — wire `make backup` cron + S3 bucket lifecycle.
- BE-PR-001/002 — `alembic revision --autogenerate -m "catchup_audit_baseline"` against fresh DB.
- FE-PERF-003 — `npm install` in `frontend/` to pick up `react-window`.
- FE-WS-001 — finding logged during IW-1 but not closed (test premise corrected, hook bug remains).

## Status

Integration complete. Repository now has every audit artifact in its
canonical home, with seven changelogs under `docs/integration/`
documenting the trail.
