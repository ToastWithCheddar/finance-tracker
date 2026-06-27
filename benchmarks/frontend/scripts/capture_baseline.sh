#!/usr/bin/env bash
#
# Capture a frontend performance baseline for finance-tracker.
#
# Steps:
#   1. Verify frontend/dist/ exists (caller is responsible for building).
#   2. Resolve git SHA and create reports/<sha>/.
#   3. Run Lighthouse CI (3 runs, autorun spawns its own preview server).
#   4. Run the dependency-free bundle analyzer.
#   5. Run the Playwright dashboard trace (uses its own webServer config).
#   6. Write meta.json (timestamp, node version, git SHA, form factor).
#
# Hard-fails on any step. Safe to re-run; output dir is namespaced by SHA + timestamp.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARNESS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${HARNESS_DIR}/../.." && pwd)"
FRONTEND_DIR="${REPO_ROOT}/frontend"
DIST_DIR="${FRONTEND_DIR}/dist"

if [[ ! -d "${DIST_DIR}" ]]; then
  echo "ERROR: ${DIST_DIR} does not exist." >&2
  echo "Build the frontend first:" >&2
  echo "  cd ${FRONTEND_DIR} && npm ci && npm run build" >&2
  exit 1
fi

GIT_SHA="$(git -C "${REPO_ROOT}" rev-parse --short HEAD 2>/dev/null || echo 'nogit')"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT_DIR="${HARNESS_DIR}/reports/${GIT_SHA}-${TS}"
mkdir -p "${REPORT_DIR}/lhci"

echo "==> Capture baseline"
echo "    repo root      : ${REPO_ROOT}"
echo "    frontend dist  : ${DIST_DIR}"
echo "    report dir     : ${REPORT_DIR}"
echo "    form factor    : ${LHCI_FORM_FACTOR:-desktop}"

# Update a 'latest' symlink for convenience (best-effort).
ln -sfn "${REPORT_DIR}" "${HARNESS_DIR}/reports/latest" || true

echo "==> [1/3] Lighthouse CI (autorun, 3 runs)"
LHCI_OUTPUT_DIR="${REPORT_DIR}/lhci" \
  npx --prefix "${HARNESS_DIR}" lhci autorun \
    --config="${HARNESS_DIR}/lighthouserc.cjs"

echo "==> [2/3] Bundle analysis"
BUNDLE_OUTPUT="${REPORT_DIR}/bundle-summary.json" \
  node "${HARNESS_DIR}/scripts/analyze_bundle.mjs"

echo "==> [3/3] Dashboard Playwright trace"
TRACE_OUTPUT="${REPORT_DIR}/dashboard-trace.json" \
  node "${HARNESS_DIR}/scripts/render_trace.mjs"

NODE_VERSION="$(node --version)"
GIT_REV_FULL="$(git -C "${REPO_ROOT}" rev-parse HEAD 2>/dev/null || echo 'nogit')"
GIT_BRANCH="$(git -C "${REPO_ROOT}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'nogit')"

cat > "${REPORT_DIR}/meta.json" <<EOF
{
  "timestamp": "${TS}",
  "git_sha_short": "${GIT_SHA}",
  "git_sha": "${GIT_REV_FULL}",
  "git_branch": "${GIT_BRANCH}",
  "node_version": "${NODE_VERSION}",
  "form_factor": "${LHCI_FORM_FACTOR:-desktop}",
  "harness_dir": "${HARNESS_DIR}",
  "frontend_dir": "${FRONTEND_DIR}"
}
EOF

echo "==> Done. Report: ${REPORT_DIR}"
