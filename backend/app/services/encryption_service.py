import base64
import logging
import os
import secrets as _secrets
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.config import settings

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Raised when encryption or decryption fails.

    BE-SEC-003: prior code silently returned the input on failure, which
    meant Plaid access tokens could be persisted *as plaintext*. We now
    bubble a typed exception so the caller can either surface a 500 or
    drop the row.
    """


class EncryptionService:
    """
    Symmetric encryption service for secrets at rest.

    Key derivation:
      - HKDF-SHA256 over `settings.SECRET_KEY` with a configurable salt
        (`settings.ENCRYPTION_KEY_SALT`, hex-encoded 32 bytes).
      - Fernet wraps the derived 32-byte key.

    Failure mode:
      - encrypt()/decrypt() raise `EncryptionError` on any failure.
        No silent plaintext fallback (BE-SEC-003).
    """

    def __init__(self):
        self._fernet = self._init_fernet()

    @staticmethod
    def _resolve_salt() -> bytes:
        raw = (settings.ENCRYPTION_KEY_SALT or "").strip()
        if not raw:
            # In production an ephemeral salt would make every previously
            # encrypted secret (e.g. Plaid access tokens) undecryptable after a
            # restart, so refuse to start instead of silently rotating it.
            if str(getattr(settings, "ENVIRONMENT", "")).lower() == "production":
                raise EncryptionError(
                    "ENCRYPTION_KEY_SALT must be set in production; refusing to "
                    "start with an ephemeral salt (would orphan existing ciphertext)."
                )
            # Dev-only ephemeral salt. Logged loudly so production deploys
            # cannot drift into this branch without somebody noticing.
            logger.warning(
                "ENCRYPTION_KEY_SALT not set; generating ephemeral salt. "
                "Cipher-text from previous runs will NOT decrypt."
            )
            return _secrets.token_bytes(32)
        try:
            salt = bytes.fromhex(raw)
        except ValueError as e:
            raise EncryptionError(
                "ENCRYPTION_KEY_SALT must be hex-encoded 32 bytes"
            ) from e
        if len(salt) < 16:
            raise EncryptionError(
                "ENCRYPTION_KEY_SALT must decode to >= 16 bytes"
            )
        return salt

    def _init_fernet(self) -> Fernet:
        secret = (settings.SECRET_KEY or "").encode("utf-8")
        if not secret:
            # Dev fallback: ephemeral key so local dev doesn't crash. In
            # production validate_required_settings() refuses to start
            # without SECRET_KEY, so this branch is unreachable there.
            logger.warning("SECRET_KEY missing; generating ephemeral encryption key (dev only)")
            return Fernet(Fernet.generate_key())

        salt = self._resolve_salt()
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            info=b"finance-tracker:encryption-service:v1",
        )
        derived = hkdf.derive(secret)
        key = base64.urlsafe_b64encode(derived)
        return Fernet(key)

    def encrypt(self, plaintext: Optional[str]) -> Optional[str]:
        if plaintext is None:
            return None
        try:
            token = self._fernet.encrypt(plaintext.encode("utf-8"))
            return token.decode("utf-8")
        except Exception as e:
            logger.error("Encryption failed", exc_info=True)
            raise EncryptionError("Encryption failed") from e

    def decrypt(self, ciphertext: Optional[str]) -> Optional[str]:
        if ciphertext is None:
            return None
        try:
            return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken as e:
            logger.error("Decryption failed: invalid token")
            raise EncryptionError("Invalid ciphertext (wrong key, corrupted, or never encrypted)") from e
        except Exception as e:
            logger.error("Decryption failed", exc_info=True)
            raise EncryptionError("Decryption failed") from e


_encryption_service_instance: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    global _encryption_service_instance
    if _encryption_service_instance is None:
        _encryption_service_instance = EncryptionService()
    return _encryption_service_instance
