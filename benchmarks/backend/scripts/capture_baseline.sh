#!/usr/bin/env bash
# capture_baseline.sh — run a 60-second headless locust load test and write
# a self-contained report under reports/<git-sha>/.
#
# Env vars:
#   BENCH_HOST       backend base URL (default http://localhost:8000)
#   BENCH_USERS      concurrent users (default 50)
#   BENCH_RAMP       spawn rate users/sec (default 5)
#   BENCH_DURATION   locust -t value (default 60s)
#   BENCH_INCLUDE_ML if set to 1, includes the ML user class
#
# Requires the stack to be running. This script does NOT start services.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

HOST="${BENCH_HOST:-http://localhost:8000}"
USERS="${BENCH_USERS:-50}"
RAMP="${BENCH_RAMP:-5}"
DURATION="${BENCH_DURATION:-60s}"

# Resolve a venv locust if present, else fall back to PATH.
LOCUST_BIN=".venv/bin/locust"
if [[ ! -x "$LOCUST_BIN" ]]; then
    LOCUST_BIN="$(command -v locust || true)"
fi
if [[ -z "${LOCUST_BIN}" || ! -x "$LOCUST_BIN" ]]; then
    echo "ERROR: locust binary not found. Install via 'pip install -e .' first." >&2
    exit 1
fi

# Resolve git sha; fall back to timestamp outside a git repo.
if SHA="$(git rev-parse --short HEAD 2>/dev/null)"; then
    :
else
    SHA="nogit-$(date +%Y%m%d-%H%M%S)"
fi

OUT_DIR="reports/${SHA}"
mkdir -p "$OUT_DIR"

echo "[capture_baseline] host=$HOST users=$USERS ramp=$RAMP duration=$DURATION sha=$SHA"
echo "[capture_baseline] writing to $OUT_DIR"

BENCH_REPORTS_DIR="$ROOT_DIR/$OUT_DIR" \
BENCH_HOST="$HOST" \
"$LOCUST_BIN" -f locust/locustfile.py \
    --host "$HOST" \
    --headless \
    -u "$USERS" -r "$RAMP" -t "$DURATION" \
    --csv "$OUT_DIR/locust" \
    --html "$OUT_DIR/locust.html" \
    --only-summary

# Emit run metadata.
cat > "$OUT_DIR/meta.json" <<EOF
{
  "git_sha": "$SHA",
  "host": "$HOST",
  "users": $USERS,
  "ramp_per_sec": $RAMP,
  "duration": "$DURATION",
  "include_ml": "${BENCH_INCLUDE_ML:-0}",
  "timestamp_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

echo "[capture_baseline] done. See $OUT_DIR/locust_stats.csv and $OUT_DIR/percentiles.csv"
