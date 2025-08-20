import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional, Union
import logging

logger = logging.getLogger(__name__)


class EncryptionService:
    """
    Service for encrypting and decrypting sensitive data like access tokens.
    Uses AES-256 encryption via Fernet (cryptography library).
    """
    
    def __init__(self):
        self._fernet: Optional[Fernet] = None
        self._initialize_encryption()
    
    def _initialize_encryption(self):
        """Initialize the encryption cipher with the key from environment."""
        encryption_key = os.getenv("ENCRYPTION_KEY")
        
        if not encryption_key:
            logger.warning("ENCRYPTION_KEY not found in environment. Encryption disabled.")
            return
        
        try:
            # If the key is a password/secret, derive a proper Fernet key
            if len(encryption_key) != 44:  # Fernet keys are 44 chars when base64 encoded
                self._fernet = self._create_fernet_from_password(encryption_key)
            else:
                # Assume it's already a properly formatted Fernet key
                self._fernet = Fernet(encryption_key.encode())
                
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            self._fernet = None
    
    def _create_fernet_from_password(self, password: str) -> Fernet:
        """Create a Fernet instance from a password using PBKDF2."""
        # Use a fixed salt for consistency (in production, consider storing this securely)
        salt = b"finance_tracker_salt_2024"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return Fernet(key)
    
    def encrypt(self, plaintext: str) -> Optional[str]:
        """
        Encrypt a plaintext string.
        
        Args:
            plaintext: The string to encrypt
            
        Returns:
            Base64 encoded encrypted string, or None if encryption fails
        """
        if not self._fernet:
            logger.warning("Encryption not available. Returning plaintext (INSECURE).")
            return plaintext
        
        if not plaintext:
            return plaintext
        
        try:
            encrypted_bytes = self._fernet.encrypt(plaintext.encode())
            return base64.urlsafe_b64encode(encrypted_bytes).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return None
    
    def decrypt(self, encrypted_text: str) -> Optional[str]:
        """
        Decrypt an encrypted string.
        
        Args:
            encrypted_text: Base64 encoded encrypted string
            
        Returns:
            Decrypted plaintext string, or None if decryption fails
        """
        if not self._fernet:
            logger.warning("Encryption not available. Returning encrypted text as-is (INSECURE).")
            return encrypted_text
        
        if not encrypted_text:
            return encrypted_text
        
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_text.encode())
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return None
    
    def is_available(self) -> bool:
        """Check if encryption is properly configured and available."""
        return self._fernet is not None
    
    @staticmethod
    def generate_key() -> str:
        """Generate a new Fernet key for use as ENCRYPTION_KEY."""
        return Fernet.generate_key().decode()


# Global instance
encryption_service = EncryptionService()