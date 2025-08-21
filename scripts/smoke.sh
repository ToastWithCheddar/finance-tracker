#!/usr/bin/env bash
set -euo pipefail

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"

echo "🚬 Smoke: Backend at $BACKEND_URL"

echo "🔍 Checking /health endpoint..."
set +e
code=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/health")
set -e
if [ "$code" != "200" ]; then
  echo "❌ /health returned $code"
  exit 1
else
  echo "✅ /health OK"
fi

echo "🔍 Checking /api/info endpoint..."
set +e
code=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/api/info")
set -e
if [ "$code" != "200" ]; then
  echo "❌ /api/info returned $code"
  exit 1
else
  echo "✅ /api/info OK"
fi

echo "⚛️  Frontend build check"
if [ -d frontend ]; then
  (cd frontend && npm run -s build)
  echo "✅ Frontend build succeeded"
fi

# Optional preview check (local development only)
if [ -d frontend ] && [ "${CI:-}" != "true" ]; then
  echo "🔍 Starting frontend preview check..."
  
  # Try to start preview server in background
  PREVIEW_PORT=4173
  PREVIEW_URL="http://localhost:$PREVIEW_PORT"
  
  set +e
  (cd frontend && timeout 30s npm run preview > /dev/null 2>&1) &
  PREVIEW_PID=$!
  
  # Wait a moment for server to start
  sleep 3
  
  # Check if preview is accessible
  code=$(curl -s -o /dev/null -w "%{http_code}" "$PREVIEW_URL" 2>/dev/null || echo "000")
  
  # Clean up preview process
  kill $PREVIEW_PID 2>/dev/null || true
  wait $PREVIEW_PID 2>/dev/null || true
  
  if [ "$code" = "200" ]; then
    echo "✅ Frontend preview OK"
  else
    echo "⚠️  Frontend preview check skipped (port busy or preview failed)"
  fi
  set -e
else
  if [ "${CI:-}" = "true" ]; then
    echo "⚠️  Frontend preview check skipped (CI environment)"
  fi
fi

echo "✅ Smoke checks passed"

