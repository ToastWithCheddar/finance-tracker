#!/usr/bin/env bash
# Lightweight repo checks. Errors propagate (INFRA-CI-002 closed).
# Run from repo root: ./scripts/check.sh
set -euo pipefail

echo "Running repo checks"

if [ -d backend ]; then
  echo "Backend: py_compile sweep"
  (cd backend && python -m py_compile $(git ls-files "*.py"))
fi

if [ -d frontend ]; then
  echo "Frontend: type-check"
  (cd frontend && npm run -s type-check)
fi

echo "Checks passed."
