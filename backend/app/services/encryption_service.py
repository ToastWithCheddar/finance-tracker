import base64
import logging
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

logger = logging.getLogger(__name__)


class EncryptionService:
    """
    Simple symmetric encryption service for secrets at rest (development-friendly).
    Uses Fernet with a key derived from SECRET_KEY. If no SECRET_KEY is set, a
    temporary in-memory key is generated (values won't be decryptable across restarts).
    """

    def __init__(self):
        self._fernet = self._init_fernet()

    def _init_fernet(self) -> Fernet:
        secret = (settings.SECRET_KEY or "").encode("utf-8")
        if not secret:
            # Dev fallback: ephemeral key so local dev doesn't crash
            logger.warning("SECRET_KEY missing; generating ephemeral encryption key (dev only)")
            key = Fernet.generate_key()
            return Fernet(key)

        # Derive a stable 32-byte key and base64-url encode for Fernet
        import hashlib
        digest = hashlib.sha256(secret).digest()  # 32 bytes
        key = base64.urlsafe_b64encode(digest)
        return Fernet(key)

    def encrypt(self, plaintext: Optional[str]) -> Optional[str]:
        if plaintext is None:
            return None
        try:
            token = self._fernet.encrypt(plaintext.encode("utf-8"))
            return token.decode("utf-8")
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            # Fail soft in dev: store plaintext to avoid breaking flows
            return plaintext

    def decrypt(self, ciphertext: Optional[str]) -> Optional[str]:
        if ciphertext is None:
            return None
        try:
            return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except (InvalidToken, Exception) as e:
            logger.warning(f"Decryption failed or invalid token; returning raw value. Error: {e}")
            # Fail soft in dev: return as-is to avoid crashes
            return ciphertext


_encryption_service_instance: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    global _encryption_service_instance
    if _encryption_service_instance is None:
        _encryption_service_instance = EncryptionService()
    return _encryption_service_instance

