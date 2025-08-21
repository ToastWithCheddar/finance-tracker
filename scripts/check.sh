#!/usr/bin/env bash
set -e

echo "🧹 Running lightweight repo checks"

if [ -d backend ]; then
  echo "🐍 Backend: syntax/type hints (optional)"
  (cd backend && python -m py_compile $(git ls-files "*.py") >/dev/null 2>&1 || true)
fi

if [ -d frontend ]; then
  echo "⚛️  Frontend: type-check"
  (cd frontend && npm run -s type-check || true)
fi

echo "✅ Checks completed (non-blocking)."

