#!/usr/bin/env bash
# ml-worker/scripts/fetch_models.sh
#
# Fetches model weights into ${MODELS_DIR:-/models} at container startup.
# Idempotent: if the target directory already contains weights, skip and exec.
#
# Selection order:
#   1) ML_MODEL_S3_URL          — s3://bucket/key/ or https://... (preferred)
#   2) HF_MODEL_ID              — HuggingFace repo id, fallback (uses huggingface_hub)
#
# Optional verification:
#   ML_MODEL_SHA256             — if set and ML_MODEL_S3_URL points at a single
#                                 archive, the file's sha256 is compared.
#
# Markers:
#   ${MODELS_DIR}/.ready        — touched on success; consumed by the readiness probe.
#
# Findings: ML-PR-005, INFRA-DOCK-005.

set -euo pipefail

MODELS_DIR="${MODELS_DIR:-/models}"
READY_FILE="${MODELS_DIR}/.ready"

log() { printf '[fetch_models] %s\n' "$*" >&2; }

mkdir -p "${MODELS_DIR}"

# ---------------------------------------------------------------------------
# Idempotency check: skip download if weights already present.
# ---------------------------------------------------------------------------
if [ -f "${READY_FILE}" ]; then
    log "ready marker present at ${READY_FILE}; skipping fetch."
    exec "$@"
fi

# Heuristic: any non-empty file other than the ready marker means we likely
# already have weights (e.g. mounted from a host path or warm volume).
if [ -n "$(find "${MODELS_DIR}" -mindepth 1 -maxdepth 3 -type f \
            \( -name '*.safetensors' -o -name '*.onnx' -o -name '*.bin' \
               -o -name '*.pkl' -o -name 'config.json' \) -print -quit 2>/dev/null)" ]; then
    log "weights already present in ${MODELS_DIR}; marking ready."
    touch "${READY_FILE}"
    exec "$@"
fi

# ---------------------------------------------------------------------------
# 1) S3 / HTTPS URL fetch
# ---------------------------------------------------------------------------
if [ -n "${ML_MODEL_S3_URL:-}" ]; then
    url="${ML_MODEL_S3_URL}"
    log "fetching from ${url}"

    case "${url}" in
        s3://*)
            command -v aws >/dev/null 2>&1 || { log "aws CLI required for s3:// URLs"; exit 1; }
            aws s3 sync "${url}" "${MODELS_DIR}/" --no-progress
            ;;
        http://*|https://*)
            archive="${MODELS_DIR}/.download"
            if command -v curl >/dev/null 2>&1; then
                curl -fL --retry 3 --retry-delay 5 -o "${archive}" "${url}"
            else
                wget -O "${archive}" "${url}"
            fi
            if [ -n "${ML_MODEL_SHA256:-}" ]; then
                log "verifying sha256"
                actual=$(sha256sum "${archive}" | awk '{print $1}')
                if [ "${actual}" != "${ML_MODEL_SHA256}" ]; then
                    log "sha256 mismatch: expected ${ML_MODEL_SHA256} got ${actual}"
                    rm -f "${archive}"
                    exit 1
                fi
            fi
            case "${url}" in
                *.tar.gz|*.tgz)  tar -xzf "${archive}" -C "${MODELS_DIR}" && rm -f "${archive}" ;;
                *.tar)           tar -xf  "${archive}" -C "${MODELS_DIR}" && rm -f "${archive}" ;;
                *.zip)           unzip -q "${archive}" -d "${MODELS_DIR}" && rm -f "${archive}" ;;
                *)               mv "${archive}" "${MODELS_DIR}/$(basename "${url}")" ;;
            esac
            ;;
        *)
            log "unsupported ML_MODEL_S3_URL scheme: ${url}"
            exit 1
            ;;
    esac

    touch "${READY_FILE}"
    log "fetch complete."
    exec "$@"
fi

# ---------------------------------------------------------------------------
# 2) HuggingFace fallback
# ---------------------------------------------------------------------------
if [ -n "${HF_MODEL_ID:-}" ]; then
    log "fetching HuggingFace model ${HF_MODEL_ID}"
    python - <<PY
import os
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id=os.environ["HF_MODEL_ID"],
    local_dir=os.environ.get("MODELS_DIR", "/models"),
    local_dir_use_symlinks=False,
    token=os.environ.get("HF_TOKEN") or None,
)
PY
    touch "${READY_FILE}"
    log "fetch complete."
    exec "$@"
fi

log "no ML_MODEL_S3_URL or HF_MODEL_ID set and ${MODELS_DIR} is empty."
log "refusing to start without weights — see docs/runbooks/model-fetch.md."
exit 1
