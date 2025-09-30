"""Unit tests for Phase 1 settings (Phase 1)."""

import pytest


class TestSignerBackendValidation:
    """Test signer backend validation."""

    def test_valid_kms_backend(self, monkeypatch):
        """Test KMS backend is accepted."""
        monkeypatch.setenv("SIGNER_BACKEND", "kms")
        monkeypatch.setenv("KMS_KEY_ID", "test-key-id")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
        monkeypatch.setenv("BASE_RPC_URL", "https://test.rpc")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")

        from src.config.settings import Settings

        settings = Settings()
        assert settings.SIGNER_BACKEND == "kms"

    def test_valid_local_backend(self, monkeypatch):
        """Test local backend is accepted."""
        monkeypatch.setenv("SIGNER_BACKEND", "local")
        monkeypatch.setenv("PRIVATE_KEY", "0x" + "a" * 64)
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
        monkeypatch.setenv("BASE_RPC_URL", "https://test.rpc")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")

        from src.config.settings import Settings

        settings = Settings()
        assert settings.SIGNER_BACKEND == "local"

    def test_invalid_signer_backend(self, monkeypatch):
        """Test invalid backend raises error."""
        monkeypatch.setenv("SIGNER_BACKEND", "invalid")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
        monkeypatch.setenv("BASE_RPC_URL", "https://test.rpc")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")

        from src.config.settings import Settings

        with pytest.raises(ValueError, match="must be either 'kms' or 'local'"):
            Settings()

    def test_default_signer_backend(self, monkeypatch):
        """Test default signer backend is kms."""
        monkeypatch.delenv("SIGNER_BACKEND", raising=False)
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
        monkeypatch.setenv("BASE_RPC_URL", "https://test.rpc")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")

        from src.config.settings import Settings

        settings = Settings()
        assert settings.SIGNER_BACKEND == "kms"


class TestEncryptionSettings:
    """Test encryption configuration settings."""

    def test_default_encryption_context(self, monkeypatch):
        """Test default encryption context."""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
        monkeypatch.setenv("BASE_RPC_URL", "https://test.rpc")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")

        from src.config.settings import Settings

        settings = Settings()
        assert settings.ENCRYPTION_CONTEXT_APP == "vanta-bot"
        assert settings.ENCRYPTION_DEK_BYTES == 32

    def test_custom_encryption_settings(self, monkeypatch):
        """Test custom encryption settings."""
        monkeypatch.setenv("ENCRYPTION_CONTEXT_APP", "custom-app")
        monkeypatch.setenv("ENCRYPTION_DEK_BYTES", "24")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
        monkeypatch.setenv("BASE_RPC_URL", "https://test.rpc")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")

        from src.config.settings import Settings

        settings = Settings()
        assert settings.ENCRYPTION_CONTEXT_APP == "custom-app"
        assert settings.ENCRYPTION_DEK_BYTES == 24
