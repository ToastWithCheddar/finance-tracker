# ML Model Fetch Runbook (ML-PR-005, INFRA-DOCK-005)

Model weights are NOT baked into the `ml-worker` image and NOT committed to
Git. They are fetched at container startup into a named volume mounted at
`/models`.

## Why

- Repo bloat: `ml_models/`, `ml-worker/models/`, `ml-worker/model_cache/`
  contain 250+ MB of binaries tracked 3x in Git history (ML-PR-005).
- Image bloat: baking weights into `ml-worker` images forces a full rebuild
  on every model rotation and pushes 250+ MB through the registry.
- Reproducibility: a SHA256-checked artifact in S3 is far easier to roll
  back than a Git LFS pointer.

## How it works

`ml-worker/Dockerfile` exposes a `prod-no-models` target whose ENTRYPOINT is
`scripts/fetch_models.sh`. The script:

1. Checks `${MODELS_DIR:-/models}/.ready` — if present, skip and `exec "$@"`.
2. Heuristically scans for any `*.safetensors`, `*.onnx`, `*.bin`, `*.pkl`,
   or `config.json` already on disk; if found, mark ready and exec.
3. Otherwise, in priority order:
   - `ML_MODEL_S3_URL` (preferred): `s3://...` (uses `aws s3 sync`) or
     `https://...` (uses `curl`/`wget`, optionally verifies `ML_MODEL_SHA256`,
     and unpacks `.tar.gz`/`.tar`/`.zip` archives).
   - `HF_MODEL_ID` (fallback): `huggingface_hub.snapshot_download`. Requires
     `huggingface_hub` in `requirements.txt` (already present).
4. Touches `${MODELS_DIR}/.ready` and execs the original celery command.

The compose `prod-no-models` service uses the same file as a readiness probe.

## Environment variables

| Variable | Required | Notes |
|---|---|---|
| `MODELS_DIR` | No (default `/models`) | Where to write weights. |
| `ML_MODEL_S3_URL` | Either this | `s3://bucket/key/` (sync) or HTTPS (single archive/file). |
| `HF_MODEL_ID` | or this | Falls back to HuggingFace Hub download. |
| `HF_TOKEN` | Optional | Required for private HF repos. |
| `ML_MODEL_SHA256` | Optional | Verifies HTTPS archive contents. |

## Publishing a new model release

1. Train / export weights locally.
2. Pack:
   ```bash
   tar -C ml_models -czf finance-classifier-v1.2.tar.gz .
   sha256sum finance-classifier-v1.2.tar.gz
   ```
3. Upload:
   ```bash
   aws s3 cp finance-classifier-v1.2.tar.gz \
     s3://ft-ml-models/finance-classifier-v1.2.tar.gz \
     --metadata "sha256=<digest>"
   ```
4. Pin the new release in production `.env`:
   ```env
   ML_MODEL_S3_URL=https://ft-ml-models.s3.amazonaws.com/finance-classifier-v1.2.tar.gz
   ML_MODEL_SHA256=<digest>
   ```
5. Roll the worker:
   ```bash
   docker compose -f docker-compose.prod.yml up -d --force-recreate ml-worker
   ```
6. Confirm `/models/.ready` exists and Celery is healthy:
   ```bash
   docker compose -f docker-compose.prod.yml exec ml-worker ls -la /models
   ```

## Rollback

Set `ML_MODEL_S3_URL` back to the prior version, delete the volume to force
re-download (`docker volume rm finance-tracker_ml_models`), and recreate.

## User action required (deferred)

- [ ] **Remove tracked weights from Git history.** Files under `ml_models/`,
      `ml-worker/models/`, `ml-worker/model_cache/`, plus
      `transaction_autocategory.csv` if large, should be removed:
      ```bash
      git rm -r --cached ml_models ml-worker/models ml-worker/model_cache
      git commit -m "ML-PR-005: stop tracking model weights"
      # Optional history rewrite:
      git filter-repo --invert-paths --path ml_models --path ml-worker/models \
                                     --path ml-worker/model_cache
      git push --force-with-lease   # coordinate with team first
      ```
- [ ] Add the directories to `.gitignore` (top-level).
- [ ] Provision the `ft-ml-models` S3 bucket and IAM user (read-only for
      runtime, write for release pipeline).
- [ ] First production rollout: validate the fetch path on a staging stack
      before flipping prod.
