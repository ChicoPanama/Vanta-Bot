"""Key Vault Service for envelope encryption with per-wallet DEKs."""

from __future__ import annotations

import base64
import logging
import os
from dataclasses import dataclass
from typing import Protocol

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)


class KeyVaultService(Protocol):
    """Protocol for key vault implementations."""

    def generate_wrapped_dek(self) -> tuple[bytes, bytes]:
        """Returns (wrapped_dek, dek_plaintext). dek_plaintext is only returned in-memory."""
        ...

    def unwrap_dek(self, wrapped_dek: bytes) -> bytes:
        """Returns dek_plaintext for runtime use."""
        ...


@dataclass
class LocalFernetKeyVault:
    """DEV ONLY: Local key vault using Fernet for development/testing.

    This is NOT used for encrypting private keys directly.
    Instead, it wraps per-wallet DEKs with a process key (rotatable).
    """

    # DEV ONLY: env var can be rotated; used to wrap per-wallet DEKs
    wrapping_key_b64: str

    def _fernet(self) -> Fernet:
        """Get Fernet instance for wrapping/unwrapping DEKs."""
        return Fernet(self.wrapping_key_b64.encode())

    def generate_wrapped_dek(self) -> tuple[bytes, bytes]:
        """Generate a new DEK and wrap it with the process key."""
        dek = os.urandom(32)  # 256-bit DEK
        # Use URL-safe base64 to make it Fernet compatible
        dek_b64 = base64.urlsafe_b64encode(dek)
        wrapped = self._fernet().encrypt(dek_b64)
        return wrapped, dek

    def unwrap_dek(self, wrapped_dek: bytes) -> bytes:
        """Unwrap a DEK using the process key."""
        try:
            dek_b64 = self._fernet().decrypt(wrapped_dek)
            return base64.urlsafe_b64decode(dek_b64)
        except Exception as e:
            logger.error(f"Failed to unwrap DEK: {e}")
            raise


@dataclass
class AwsKmsKeyVault:
    """Production key vault using AWS KMS for envelope encryption."""

    kms_key_id: str
    kms_client: boto3.client  # type: ignore

    def generate_wrapped_dek(self) -> tuple[bytes, bytes]:
        """Generate a new DEK wrapped by KMS."""
        try:
            resp = self.kms_client.generate_data_key(
                KeyId=self.kms_key_id, KeySpec="AES_256"
            )
            return resp["CiphertextBlob"], resp["Plaintext"]
        except Exception as e:
            logger.error(f"Failed to generate wrapped DEK from KMS: {e}")
            raise

    def unwrap_dek(self, wrapped_dek: bytes) -> bytes:
        """Unwrap a DEK using KMS."""
        try:
            resp = self.kms_client.decrypt(
                CiphertextBlob=wrapped_dek, KeyId=self.kms_key_id
            )
            return resp["Plaintext"]
        except Exception as e:
            logger.error(f"Failed to unwrap DEK from KMS: {e}")
            raise


class WalletEncryption:
    """Handles encryption/decryption of wallet private keys using envelope encryption."""

    def __init__(self, key_vault: KeyVaultService):
        self.key_vault = key_vault

    def encrypt_private_key(self, private_key_hex: str, dek: bytes) -> bytes:
        """Encrypt private key using AES-GCM with provided DEK."""
        try:
            aesgcm = AESGCM(dek)
            nonce = os.urandom(12)  # 96-bit nonce for GCM
            private_key_bytes = bytes.fromhex(private_key_hex)
            ciphertext = aesgcm.encrypt(nonce, private_key_bytes, None)
            # Prepend nonce to ciphertext for storage
            return nonce + ciphertext
        except Exception as e:
            logger.error(f"Failed to encrypt private key: {e}")
            raise

    def decrypt_private_key(self, ciphertext: bytes, dek: bytes) -> str:
        """Decrypt private key using AES-GCM with provided DEK."""
        try:
            aesgcm = AESGCM(dek)
            nonce = ciphertext[:12]
            encrypted_data = ciphertext[12:]
            private_key_bytes = aesgcm.decrypt(nonce, encrypted_data, None)
            return private_key_bytes.hex()
        except Exception as e:
            logger.error(f"Failed to decrypt private key: {e}")
            raise

    def create_encrypted_wallet(self, private_key_hex: str) -> tuple[bytes, bytes]:
        """Create encrypted wallet with new DEK."""
        wrapped_dek, dek = self.key_vault.generate_wrapped_dek()
        encrypted_privkey = self.encrypt_private_key(private_key_hex, dek)
        return wrapped_dek, encrypted_privkey

    def decrypt_wallet(self, wrapped_dek: bytes, encrypted_privkey: bytes) -> str:
        """Decrypt wallet private key."""
        dek = self.key_vault.unwrap_dek(wrapped_dek)
        return self.decrypt_private_key(encrypted_privkey, dek)
