"""Envelope encryption utilities (AES-GCM + KMS) for DB secrets (Phase 1)."""

import logging
from dataclasses import dataclass
from typing import Any

import boto3
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

logger = logging.getLogger(__name__)


@dataclass
class CipherBlob:
    """Encrypted data blob with KMS-wrapped DEK."""

    key_id: str
    dek_encrypted: bytes
    iv: bytes
    tag: bytes
    ciphertext: bytes


# Global KMS client (lazy initialization)
_kms_client = None


def _get_kms_client() -> Any:
    """Get or create KMS client."""
    global _kms_client
    if _kms_client is None:
        from src.config.settings import settings

        _kms_client = boto3.client("kms", region_name=settings.AWS_REGION)
    return _kms_client


def generate_dek() -> tuple[bytes, bytes, str]:
    """Generate a new Data Encryption Key (DEK) and wrap it with KMS.

    Returns:
        Tuple of (dek_plaintext, dek_encrypted, key_id)
    """
    from src.config.settings import settings

    # Generate random DEK
    dek_plain = get_random_bytes(settings.ENCRYPTION_DEK_BYTES)

    # Wrap DEK with KMS
    key_id = settings.KMS_KEY_ID or settings.AWS_KMS_KEY_ID
    if not key_id:
        raise RuntimeError("KMS_KEY_ID not configured for envelope encryption")

    kms = _get_kms_client()
    response = kms.encrypt(
        KeyId=key_id,
        Plaintext=dek_plain,
        EncryptionContext={"app": settings.ENCRYPTION_CONTEXT_APP},
    )

    return dek_plain, response["CiphertextBlob"], response["KeyId"]


def rewrap_encrypted_dek(old_ciphertext_blob: bytes) -> bytes:
    """Decrypt old DEK with old key, re-encrypt with current KMS_KEY_ID.

    Used for key rotation.

    Args:
        old_ciphertext_blob: Previously encrypted DEK

    Returns:
        Newly encrypted DEK blob
    """
    from src.config.settings import settings

    kms = _get_kms_client()

    # Decrypt old DEK
    plaintext_dek = kms.decrypt(
        CiphertextBlob=old_ciphertext_blob,
        EncryptionContext={"app": settings.ENCRYPTION_CONTEXT_APP},
    )["Plaintext"]

    # Re-encrypt with current key
    key_id = settings.KMS_KEY_ID or settings.AWS_KMS_KEY_ID
    new_blob = kms.encrypt(
        KeyId=key_id,
        Plaintext=plaintext_dek,
        EncryptionContext={"app": settings.ENCRYPTION_CONTEXT_APP},
    )["CiphertextBlob"]

    return new_blob


def aes_gcm_encrypt(plaintext: bytes, dek_plain: bytes) -> tuple[bytes, bytes, bytes]:
    """Encrypt data with AES-GCM using DEK.

    Args:
        plaintext: Data to encrypt
        dek_plain: Plaintext DEK (32 bytes)

    Returns:
        Tuple of (iv, ciphertext, tag)
    """
    iv = get_random_bytes(12)  # 96-bit IV for GCM
    cipher = AES.new(dek_plain, AES.MODE_GCM, nonce=iv)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    return iv, ciphertext, tag


def aes_gcm_decrypt(
    iv: bytes, ciphertext: bytes, tag: bytes, dek_plain: bytes
) -> bytes:
    """Decrypt AES-GCM encrypted data.

    Args:
        iv: Initialization vector
        ciphertext: Encrypted data
        tag: Authentication tag
        dek_plain: Plaintext DEK

    Returns:
        Decrypted plaintext

    Raises:
        ValueError: If authentication fails
    """
    cipher = AES.new(dek_plain, AES.MODE_GCM, nonce=iv)
    return cipher.decrypt_and_verify(ciphertext, tag)


def encrypt_blob(plaintext: bytes) -> CipherBlob:
    """Encrypt data with envelope encryption (KMS + AES-GCM).

    Args:
        plaintext: Data to encrypt

    Returns:
        CipherBlob with all encrypted components
    """
    # Generate and wrap DEK
    dek_plain, dek_encrypted, key_id = generate_dek()

    # Encrypt data with DEK
    iv, ciphertext, tag = aes_gcm_encrypt(plaintext, dek_plain)

    return CipherBlob(
        key_id=key_id,
        dek_encrypted=dek_encrypted,
        iv=iv,
        tag=tag,
        ciphertext=ciphertext,
    )


def decrypt_blob(blob: CipherBlob) -> bytes:
    """Decrypt envelope-encrypted data.

    Args:
        blob: CipherBlob to decrypt

    Returns:
        Decrypted plaintext
    """
    from src.config.settings import settings

    # Unwrap DEK with KMS
    kms = _get_kms_client()
    plaintext_dek = kms.decrypt(
        CiphertextBlob=blob.dek_encrypted,
        EncryptionContext={"app": settings.ENCRYPTION_CONTEXT_APP},
    )["Plaintext"]

    # Decrypt data with DEK
    return aes_gcm_decrypt(blob.iv, blob.ciphertext, blob.tag, plaintext_dek)
