# Audit Archive

This directory contains the historical risk register and improvement-section briefs from the 8-wave audit (W1–W8) that hardened this codebase between 2026-04 and 2026-04-27. The register is at `findings.csv`; per-section briefs are in `improvement-sections/`. The integration of the audit work into the canonical tree is documented under `docs/integration/`.

## Contents

- `AUDIT_OVERVIEW.md` — original `audit/README.md`, preserved as historical context.
- `findings.csv` — canonical risk register (~79 rows).
- `findings-detail.md` — long-form findings narrative.
- `findings-readme.md` — (if present) original findings index.
- `snapshot/` — frozen architecture / map docs taken at audit start.
- `improvement-sections/` — per-pillar agent briefs A–F (performance, testing, observability, production-readiness, security, ML revival).

## Where the work landed

| Audit area | Canonical home |
|---|---|
| Tests | `backend/tests/`, `frontend/tests/`, `ml-worker/tests/`, `e2e/` |
| Benchmarks | `benchmarks/` |
| Observability config | `ops/observability/` |
| CI | `.github/workflows/ci.yml` |
| Compose / Makefile | repo root |
| Runbooks | `docs/runbooks/` |
