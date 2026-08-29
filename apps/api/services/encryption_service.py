import base64
import hashlib
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from config import settings
from utils.logging import get_logger

logger = get_logger("EncryptionService")

class EncryptionService:
    """
    Provides symmetric token encryption and decryption at rest using Fernet
    (AES-128-CBC + HMAC-SHA256) keyed by the server's ENCRYPTION_SECRET.
    """

    def __init__(self, secret: Optional[str] = None):
        raw_secret = secret or getattr(settings, "ENCRYPTION_SECRET", "reflow_default_secret_key_32_bytes_len")
        # Derive deterministic 32-byte key via SHA-256 and base64-encode for Fernet
        key_bytes = hashlib.sha256(raw_secret.encode("utf-8")).digest()
        self._fernet_key = base64.urlsafe_b64encode(key_bytes)
        self._fernet = Fernet(self._fernet_key)

    def encrypt_token(self, plain_text: Optional[str]) -> Optional[str]:
        """Encrypts a plaintext token into a secure ciphertext string."""
        if not plain_text:
            return None
        try:
            encrypted_bytes = self._fernet.encrypt(plain_text.encode("utf-8"))
            return encrypted_bytes.decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to encrypt token: {e}")
            raise ValueError("Token encryption error")

    def decrypt_token(self, cipher_text: Optional[str]) -> Optional[str]:
        """Decrypts a ciphertext string back into the original plaintext token."""
        if not cipher_text:
            return None
        try:
            decrypted_bytes = self._fernet.decrypt(cipher_text.encode("utf-8"))
            return decrypted_bytes.decode("utf-8")
        except InvalidToken:
            logger.error("Failed to decrypt token: Invalid token or key mismatch.")
            raise ValueError("Invalid encryption token")
        except Exception as e:
            logger.error(f"Failed to decrypt token: {e}")
            raise ValueError("Token decryption error")

encryption_service = EncryptionService()
