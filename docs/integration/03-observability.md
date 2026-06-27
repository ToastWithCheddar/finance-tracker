# IW-3 — Observability + logging cleanup

## Summary
Stood up `ops/observability/` as the canonical home for the OpenTelemetry
collector config and Grafana dashboards. Deleted the duplicate logger sources
under `audit/50-logging/` (the live copies in `backend/app/logging_config.py`,
`ml-worker/app/logging_config.py`, and `frontend/src/utils/logger.ts` are
canonical-by-design). Rewrote the logging README as
`docs/runbooks/observability-stack.md`, dropping the duplicate-modules
workaround narrative and pointing all paths at the new locations. The
`audit/50-logging/` directory is left empty for IW-6 to delete with the rest
of `audit/`.

## Files moved
| Source | Destination | Notes |
|---|---|---|
| `audit/50-logging/otel/` | `ops/observability/otel/` | volume mounts in `docker-compose.observability.yml` updated |
| `audit/50-logging/grafana/` | `ops/observability/grafana/` | only `dashboards/backend-overview.json` is present |
| `audit/50-logging/README.md` | `docs/runbooks/observability-stack.md` | rewritten for canonical paths |

## Files deleted
- `audit/50-logging/structlog_config.py` — canonical copies live at `backend/app/logging_config.py` and `ml-worker/app/logging_config.py`.
- `audit/50-logging/frontend/logger.ts` — canonical at `frontend/src/utils/logger.ts`.
- `audit/50-logging/__pycache__/` — untracked compiled artifacts.

## Files edited (path rewrites only)
- `audit/60-ci/docker-compose.observability.yml` — header comment plus all five volume mounts switched from `../50-logging/...` to `./ops/observability/...` (post-move-to-repo-root paths). IW-2 will move the file itself to repo root.

## Verification
```
$ test -f backend/app/logging_config.py && test -f ml-worker/app/logging_config.py && test -f frontend/src/utils/logger.ts
(exit 0)

$ python3 -m py_compile backend/app/logging_config.py ml-worker/app/logging_config.py
py_compile OK

$ python3 -c "import yaml; yaml.safe_load(open('ops/observability/otel/collector-config.yaml'))"
yaml OK

$ python3 -c "import json; json.load(open('ops/observability/grafana/dashboards/backend-overview.json'))"
json OK

$ grep -rn "audit/50-logging\|audit\.50_logging" backend frontend ml-worker ops docs | grep -v 'docs/integration/'
(no matches)
```

Note: source files in `audit/50-logging/` were untracked in git (never staged
during W5), so `git mv` was not applicable. Plain `mv`/`rm` were used; the
destinations under `ops/observability/` and `docs/runbooks/` will be picked up
by `git add` in the integration commit.

## Open follow-ups
- IW-2 will move `docker-compose.observability.yml` from `audit/60-ci/` to the
  repo root; the relative paths edited in Step 6 already assume the root
  location, so no further edits are needed once IW-2 moves the file.
- `frontend/src/utils/logger.ts` and the two backend `logging_config.py` files
  still carry header comments referencing `audit/50-logging/...` as the
  canonical source. Updating those comments was out of scope for IW-3 (touch
  list excludes those files); IW-6 or a follow-up sweep should drop the stale
  references when `audit/` is removed.
