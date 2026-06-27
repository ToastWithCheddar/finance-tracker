"""BE-SEC-003 — Encryption key-rotation diagnostic helper.

This module is intentionally **read-only**. It does NOT auto-rotate stored
ciphertexts; that decision belongs to a runbook (see
`docs/runbooks/encryption-migration.md`). Its job is to scan the columns
that hold encrypted values and report what is decryptable under the current
key, what is *not*, and what looks suspiciously like plaintext (a likely
fallout of the old fail-soft `encryption_service.py` behavior — BE-SEC-003).

Usage:
    python -m app.services.encryption_migration

Exits 0 on success regardless of findings; the report goes to stdout/stderr.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from typing import Iterable, List, Tuple

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.services.encryption_service import EncryptionError, get_encryption_service

logger = logging.getLogger(__name__)


# (table_name, column_name) — extend as new encrypted columns are introduced.
# Keep this list small and explicit; the helper deliberately does NOT introspect.
ENCRYPTED_COLUMNS: List[Tuple[str, str]] = [
    ("accounts", "plaid_access_token"),
    ("accounts", "plaid_item_id"),
]


@dataclass
class ColumnReport:
    table: str
    column: str
    total: int = 0
    null_or_empty: int = 0
    decryptable: int = 0
    undecryptable: int = 0
    suspected_plaintext: int = 0
    samples_undecryptable: List[str] = field(default_factory=list)


def _looks_like_fernet(value: str) -> bool:
    # Fernet tokens are urlsafe-b64 and start with "gAAAAA" once the version
    # byte is encoded. This is a heuristic, not a guarantee.
    return isinstance(value, str) and value.startswith("gAAAAA")


def _scan_column(db: Session, table: str, column: str) -> ColumnReport:
    report = ColumnReport(table=table, column=column)

    # Cheap existence check so missing columns don't crash the diagnostic.
    insp = inspect(db.get_bind())
    if table not in insp.get_table_names():
        logger.warning(f"Skip {table}.{column}: table not present")
        return report
    if column not in {c["name"] for c in insp.get_columns(table)}:
        logger.warning(f"Skip {table}.{column}: column not present")
        return report

    rows: Iterable[Tuple[str]] = db.execute(
        text(f"SELECT {column} FROM {table}")
    ).all()

    enc = get_encryption_service()
    for (value,) in rows:
        report.total += 1
        if not value:
            report.null_or_empty += 1
            continue
        if not _looks_like_fernet(value):
            report.suspected_plaintext += 1
            continue
        try:
            enc.decrypt(value)
            report.decryptable += 1
        except EncryptionError:
            report.undecryptable += 1
            if len(report.samples_undecryptable) < 3:
                # Truncated sample — never log a full secret.
                report.samples_undecryptable.append(value[:12] + "…")
    return report


def run() -> int:
    db = SessionLocal()
    exit_code = 0
    try:
        for table, column in ENCRYPTED_COLUMNS:
            r = _scan_column(db, table, column)
            print(
                f"[{r.table}.{r.column}] total={r.total} "
                f"null={r.null_or_empty} decryptable={r.decryptable} "
                f"undecryptable={r.undecryptable} "
                f"suspected_plaintext={r.suspected_plaintext}"
            )
            if r.suspected_plaintext or r.undecryptable:
                # Non-zero but don't fail the process; let CI/operators decide.
                print(
                    f"  WARNING: {r.suspected_plaintext} suspected plaintext, "
                    f"{r.undecryptable} undecryptable rows. See "
                    f"docs/runbooks/encryption-migration.md."
                )
                if r.samples_undecryptable:
                    print(f"  samples (truncated): {r.samples_undecryptable}")
    finally:
        db.close()
    return exit_code


if __name__ == "__main__":  # pragma: no cover
    sys.exit(run())
