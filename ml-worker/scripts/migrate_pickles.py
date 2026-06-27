"""ML-SEC-001 — Migrate legacy `.pkl` category prototypes to safetensors.

Usage:
    ALLOW_LEGACY_PICKLE_LOAD=1 python -m scripts.migrate_pickles \
        ml_models/prototypes.pkl [more.pkl ...]

For each input file we:
  1. Load the pickle (gated by ALLOW_LEGACY_PICKLE_LOAD=1 — refusing to load
     pickles silently is the whole point of the finding).
  2. Re-save as `<base>.safetensors` plus a `.meta.json` sidecar.
  3. Leave the original `.pkl` in place; the operator can `git rm` it after
     verifying the safetensors copy loads cleanly.
"""

from __future__ import annotations

import json
import os
import pickle
import sys
from pathlib import Path

import numpy as np


def _ensure_pickle_allowed() -> None:
    if os.environ.get("ALLOW_LEGACY_PICKLE_LOAD") != "1":
        sys.stderr.write(
            "Refusing to load pickles. Set ALLOW_LEGACY_PICKLE_LOAD=1 to opt in.\n"
        )
        sys.exit(2)


def migrate_one(src: Path) -> int:
    if not src.exists() or src.suffix != ".pkl":
        sys.stderr.write(f"skip: {src} (not a .pkl file)\n")
        return 1

    with src.open("rb") as f:
        data = pickle.load(f)  # noqa: S301 — gated behind env flag

    prototypes = data.get("prototypes") if isinstance(data, dict) else None
    if not prototypes:
        sys.stderr.write(f"skip: {src} (no 'prototypes' key)\n")
        return 1

    try:
        from safetensors.numpy import save_file as st_save
    except Exception as e:
        sys.stderr.write(f"safetensors missing: {e}\n")
        return 2

    base = src.with_suffix("")
    st_path = base.with_suffix(".safetensors")
    meta_path = Path(str(base) + ".meta.json")

    tensors = {str(k): np.asarray(v, dtype=np.float32) for k, v in prototypes.items()}
    st_save(tensors, str(st_path))

    meta = {
        "model_version": data.get("model_version", "v1.0"),
        "model_name": data.get("model_name"),
        "categories": list(tensors.keys()),
        "format": "safetensors-v1",
        "migrated_from": str(src.name),
    }
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"migrated: {src} -> {st_path} ({len(tensors)} prototypes)")
    return 0


def main(argv: list[str]) -> int:
    _ensure_pickle_allowed()
    if not argv:
        print(__doc__)
        return 0
    rc = 0
    for path in argv:
        rc |= migrate_one(Path(path))
    return rc


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
