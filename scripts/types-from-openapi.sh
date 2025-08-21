#!/usr/bin/env bash
set -euo pipefail

SPEC_PATH="memory/contracts/backend_openapi.json"
OUT_DIR="frontend/src/api/generated"
BACKEND_URL="${BACKEND_URL:-}"

usage() {
  echo "Usage: BACKEND_URL=http://localhost:8000 $0 [--fetch]"
  echo "  --fetch     Fetch and update spec from \$BACKEND_URL/openapi.json before generating"
}

FETCH=false
if [[ "${1:-}" == "--fetch" ]]; then
  FETCH=true
fi

if [[ "$FETCH" == true ]]; then
  if [[ -z "$BACKEND_URL" ]]; then
    echo "❌ --fetch provided but BACKEND_URL is empty."
    usage
    exit 1
  fi
  echo "🌐 Fetching OpenAPI from $BACKEND_URL/openapi.json"
  curl -sf "$BACKEND_URL/openapi.json" > "$SPEC_PATH"
fi

if [ ! -f "$SPEC_PATH" ]; then
  echo "❌ Spec not found at $SPEC_PATH"
  echo "Run backend and save $BACKEND_URL/openapi.json (or http://localhost:8000/openapi.json) to this path, or rerun with --fetch."
  exit 1
fi

# Basic validation: ensure OpenAPI 3.x
if ! grep -q '"openapi"\s*:\s*"3\.' "$SPEC_PATH"; then
  echo "❌ Spec at $SPEC_PATH is not OpenAPI 3.x or file is not valid JSON."
  echo "Tip: Fetch from a running FastAPI app: BACKEND_URL=http://localhost:8000 $0 --fetch"
  exit 1
fi

mkdir -p "$OUT_DIR"

echo "🛠️  Generating TypeScript types + client from $SPEC_PATH"

if ! command -v npx >/dev/null 2>&1; then
  echo "❌ npx not found. Install Node.js (>=18)"
  exit 1
fi

# Prefer openapi-typescript; install if missing in local cache
npx --yes openapi-typescript "$SPEC_PATH" --output "$OUT_DIR/types.ts"

# Optional: generate a simple fetch wrapper using the spec (placeholder)
cat > "$OUT_DIR/client.ts" <<'EOF'
// Minimal API client placeholder. Prefer calling typed endpoints from types.ts.
export const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function apiFetch(path: string, init?: RequestInit) {
  const res = await fetch(`${apiBase}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status}: ${text}`);
  }
  const ct = res.headers.get('content-type') || '';
  return ct.includes('application/json') ? res.json() : res.text();
}
EOF

echo "✅ Types generated at $OUT_DIR"
