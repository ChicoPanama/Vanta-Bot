"""Unit tests for encrypted SQLAlchemy types (Phase 1)."""

import pytest
from moto import mock_aws


@mock_aws
class TestEncryptedTypes:
    """Test encrypted SQLAlchemy column types."""

    def test_encrypted_bytes_round_trip(self, monkeypatch):
        """Test EncryptedBytes type encryption/decryption."""
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
        for mod in ["src.config.settings", "src.security.crypto", "src.database.types"]:
            if mod in sys.modules:
                del sys.modules[mod]

        from src.database.types import EncryptedBytes

        encrypted_type = EncryptedBytes()

        # Test data
        original = b"secret data"

        # Encrypt (simulate bind)
        encrypted = encrypted_type.process_bind_param(original, None)
        assert encrypted is not None
        assert encrypted != original
        assert isinstance(encrypted, bytes)

        # Decrypt (simulate result)
        decrypted = encrypted_type.process_result_value(encrypted, None)
        assert decrypted == original

    def test_encrypted_json_round_trip(self, monkeypatch):
        """Test EncryptedJSON type encryption/decryption."""
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
        for mod in ["src.config.settings", "src.security.crypto", "src.database.types"]:
            if mod in sys.modules:
                del sys.modules[mod]

        from src.database.types import EncryptedJSON

        encrypted_type = EncryptedJSON()

        # Test data
        original = {"key": "value", "number": 123, "nested": {"data": "test"}}

        # Encrypt (simulate bind)
        encrypted = encrypted_type.process_bind_param(original, None)
        assert encrypted is not None
        assert isinstance(encrypted, bytes)

        # Decrypt (simulate result)
        decrypted = encrypted_type.process_result_value(encrypted, None)
        assert decrypted == original

    def test_encrypted_string_round_trip(self, monkeypatch):
        """Test EncryptedString type encryption/decryption."""
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
        for mod in ["src.config.settings", "src.security.crypto", "src.database.types"]:
            if mod in sys.modules:
                del sys.modules[mod]

        from src.database.types import EncryptedString

        encrypted_type = EncryptedString()

        # Test data
        original = "sensitive API key"

        # Encrypt (simulate bind)
        encrypted = encrypted_type.process_bind_param(original, None)
        assert encrypted is not None
        assert isinstance(encrypted, bytes)

        # Decrypt (simulate result)
        decrypted = encrypted_type.process_result_value(encrypted, None)
        assert decrypted == original

    def test_encrypted_types_handle_none(self):
        """Test encrypted types handle None values."""
        from src.database.types import EncryptedBytes, EncryptedJSON, EncryptedString

        types_to_test = [EncryptedBytes(), EncryptedJSON(), EncryptedString()]

        for encrypted_type in types_to_test:
            encrypted = encrypted_type.process_bind_param(None, None)
            assert encrypted is None

            decrypted = encrypted_type.process_result_value(None, None)
            assert decrypted is None
