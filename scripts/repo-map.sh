#!/usr/bin/env bash
set -euo pipefail

echo "🔎 Repo map (backend routes and FE services)"

echo "\n== Backend routers (FastAPI) =="
rg -n "^@router\.(get|post|put|delete)|APIRouter\(|include_router\(" backend/app 2>/dev/null | sed -E 's/^/  /'

echo "\n== Backend router includes (prefixes) =="
rg -n "app.include_router\(" backend/app/main.py 2>/dev/null | sed -E 's/^/  /'

echo "\n== Frontend services =="
rg --files frontend/src/services | sed -E 's/^/  /'

echo "\nTip: curate links in memory/integration-map.md"

