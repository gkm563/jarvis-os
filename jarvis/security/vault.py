"""
AES-256 Encrypted Vault Module for JARVIS OS.
Provides secure storage at rest for API keys, passwords, and sensitive tokens.
"""

import base64
import os
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from jarvis.core.interfaces import BaseSecurityVault
from jarvis.core.exceptions import VaultError
from jarvis.config.settings import settings
from jarvis.utils.logger import get_logger

logger = get_logger("SecurityVault")


class AESVault(BaseSecurityVault):
    """
    AES-256 Fernet-backed Vault implementation utilizing PBKDF2HMAC key derivation.
    """

    def __init__(self, master_password: Optional[str] = None, salt: Optional[bytes] = None):
        self.master_password = (master_password or settings.VAULT_MASTER_KEY).encode("utf-8")
        self.salt = salt or b"jarvis_os_static_salt_bytes_v1"
        self._fernet = self._derive_fernet_key()
        self._in_memory_store = {}
        logger.info("AES-256 Vault initialized successfully")

    def _derive_fernet_key(self) -> Fernet:
        """Derives a 32-byte URL-safe Fernet key using PBKDF2HMAC SHA256."""
        try:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self.salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.master_password))
            return Fernet(key)
        except Exception as e:
            raise VaultError(f"Failed to derive vault encryption key: {str(e)}")

    def store_secret(self, service: str, secret: str) -> bool:
        """
        Encrypts and stores a secret key under a service identifier.

        Args:
            service (str): Service key identifier.
            secret (str): Raw unencrypted string secret.

        Returns:
            bool: True if stored successfully.
        """
        try:
            encrypted_bytes = self._fernet.encrypt(secret.encode("utf-8"))
            self._in_memory_store[service] = encrypted_bytes
            logger.info(f"Secret for '{service}' encrypted and stored in vault", extra={"audit": True})
            return True
        except Exception as e:
            logger.error(f"Failed to store secret for '{service}': {str(e)}")
            raise VaultError(f"Encryption failed for {service}: {str(e)}")

    def get_secret(self, service: str) -> Optional[str]:
        """
        Decrypts and returns a secret stored in the vault.

        Args:
            service (str): Service key identifier.

        Returns:
            Optional[str]: Decrypted raw secret, or None if not found.
        """
        encrypted_bytes = self._in_memory_store.get(service)
        if not encrypted_bytes:
            logger.warning(f"Requested secret for '{service}' not found in vault")
            return None

        try:
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to decrypt secret for '{service}': {str(e)}")
            raise VaultError(f"Decryption failed for {service}: {str(e)}")

    def delete_secret(self, service: str) -> bool:
        """Removes a secret from the vault."""
        if service in self._in_memory_store:
            del self._in_memory_store[service]
            logger.info(f"Secret for '{service}' purged from vault", extra={"audit": True})
            return True
        return False
