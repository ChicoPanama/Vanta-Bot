"""Unit tests for envelope encryption (Phase 1)."""

import pytest
from moto import mock_aws


@mock_aws
class TestEnvelopeEncryption:
    """Test envelope encryption with mocked KMS."""

    def test_round_trip_crypto(self, monkeypatch):
        """Test encrypt/decrypt round trip."""
        import sys

        import boto3

        # Setup mocked KMS
        kms = boto3.client("kms", region_name="us-east-1")
        key = kms.create_key()["KeyMetadata"]["KeyId"]

        monkeypatch.setenv("KMS_KEY_ID", key)
        monkeypatch.setenv("AWS_REGION", "us-east-1")
        monkeypatch.setenv("ENCRYPTION_CONTEXT_APP", "test-app")
        monkeypatch.setenv("ENCRYPTION_DEK_BYTES", "32")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test")
        monkeypatch.setenv("BASE_RPC_URL", "https://test.rpc")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")

        # Reload settings module to pick up env vars
        if "src.config.settings" in sys.modules:
            del sys.modules["src.config.settings"]
        if "src.security.crypto" in sys.modules:
            del sys.modules["src.security.crypto"]

        from src.security.crypto import decrypt_blob, encrypt_blob

        # Test data
        data = b"secret123"

        # Encrypt
        blob = encrypt_blob(data)

        # Verify blob structure (KMS returns ARN, not raw key ID)
        assert key in blob.key_id  # blob.key_id is full ARN
        assert len(blob.dek_encrypted) > 0
        assert len(blob.iv) == 12  # GCM IV
        assert len(blob.tag) == 16  # GCM tag
        assert len(blob.ciphertext) > 0

        # Decrypt
        decrypted = decrypt_blob(blob)
        assert decrypted == data

    def test_rewrap_dek(self, monkeypatch):
        """Test DEK rewrapping for key rotation."""
        import sys

        import boto3

        # Setup mocked KMS
        kms = boto3.client("kms", region_name="us-east-1")
        old_key = kms.create_key()["KeyMetadata"]["KeyId"]
        new_key = kms.create_key()["KeyMetadata"]["KeyId"]

        # Use old key
        monkeypatch.setenv("KMS_KEY_ID", old_key)
        monkeypatch.setenv("AWS_REGION", "us-east-1")
        monkeypatch.setenv("ENCRYPTION_CONTEXT_APP", "test-app")
        monkeypatch.setenv("ENCRYPTION_DEK_BYTES", "32")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test")
        monkeypatch.setenv("BASE_RPC_URL", "https://test.rpc")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")

        # Reload modules
        for mod in ["src.config.settings", "src.security.crypto"]:
            if mod in sys.modules:
                del sys.modules[mod]

        from src.security.crypto import generate_dek, rewrap_encrypted_dek

        # Generate DEK with old key
        dek_plain, dek_encrypted_old, _ = generate_dek()

        # Switch to new key
        monkeypatch.setenv("KMS_KEY_ID", new_key)

        # Reload settings/crypto again
        for mod in ["src.config.settings", "src.security.crypto"]:
            if mod in sys.modules:
                del sys.modules[mod]

        from src.security.crypto import rewrap_encrypted_dek as rewrap_func

        # Rewrap DEK
        dek_encrypted_new = rewrap_func(dek_encrypted_old)

        # Verify we can decrypt with new key
        decrypted_dek = kms.decrypt(
            CiphertextBlob=dek_encrypted_new,
            EncryptionContext={"app": "test-app"},
        )["Plaintext"]

        assert decrypted_dek == dek_plain

    def test_aes_gcm_encrypt_decrypt(self):
        """Test AES-GCM encryption/decryption."""
        from Crypto.Random import get_random_bytes

        from src.security.crypto import aes_gcm_decrypt, aes_gcm_encrypt

        dek = get_random_bytes(32)
        plaintext = b"test data"

        iv, ciphertext, tag = aes_gcm_encrypt(plaintext, dek)

        assert len(iv) == 12
        assert len(tag) == 16
        assert ciphertext != plaintext

        decrypted = aes_gcm_decrypt(iv, ciphertext, tag, dek)
        assert decrypted == plaintext

    def test_encrypt_different_plaintexts_different_ciphertexts(self, monkeypatch):
        """Test that same plaintext produces different ciphertexts (random IV)."""
        import sys

        import boto3

        # Setup mocked KMS
        kms = boto3.client("kms", region_name="us-east-1")
        key = kms.create_key()["KeyMetadata"]["KeyId"]

        monkeypatch.setenv("KMS_KEY_ID", key)
        monkeypatch.setenv("AWS_REGION", "us-east-1")
        monkeypatch.setenv("ENCRYPTION_CONTEXT_APP", "test-app")
        monkeypatch.setenv("ENCRYPTION_DEK_BYTES", "32")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test")
        monkeypatch.setenv("BASE_RPC_URL", "https://test.rpc")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")

        # Reload modules
        for mod in ["src.config.settings", "src.security.crypto"]:
            if mod in sys.modules:
                del sys.modules[mod]

        from src.security.crypto import encrypt_blob

        data = b"same data"

        blob1 = encrypt_blob(data)
        blob2 = encrypt_blob(data)

        # Different IVs and ciphertexts
        assert blob1.iv != blob2.iv
        assert blob1.ciphertext != blob2.ciphertext
