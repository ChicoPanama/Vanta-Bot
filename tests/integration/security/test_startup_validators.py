"""Integration tests for startup validators (Phase 1)."""

import pytest


class TestStartupValidators:
    """Test startup configuration validators."""

    def test_validate_kms_config_success(self, monkeypatch):
        """Test KMS config validation passes with valid settings."""
        monkeypatch.setenv("SIGNER_BACKEND", "kms")
        monkeypatch.setenv("KMS_KEY_ID", "test-key-id")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test")
        monkeypatch.setenv("BASE_RPC_URL", "https://test.rpc")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")

        from src.startup.validators import validate_signer_config

        # Should not raise
        validate_signer_config()

    def test_validate_kms_config_missing_key(self, monkeypatch):
        """Test KMS config validation fails without key ID."""
        import sys
        
        monkeypatch.setenv("SIGNER_BACKEND", "kms")
        monkeypatch.delenv("KMS_KEY_ID", raising=False)
        monkeypatch.delenv("AWS_KMS_KEY_ID", raising=False)
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test")
        monkeypatch.setenv("BASE_RPC_URL", "https://test.rpc")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")

        # Reload modules
        for mod in ["src.config.settings", "src.startup.validators"]:
            if mod in sys.modules:
                del sys.modules[mod]

        from src.startup.validators import validate_signer_config

        with pytest.raises(RuntimeError, match="KMS_KEY_ID"):
            validate_signer_config()

    def test_validate_local_config_warns(self, monkeypatch):
        """Test local config validation emits warning."""
        import sys
        
        monkeypatch.setenv("SIGNER_BACKEND", "local")
        monkeypatch.setenv("PRIVATE_KEY", "0x" + "a" * 64)
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test")
        monkeypatch.setenv("BASE_RPC_URL", "https://test.rpc")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")

        # Reload modules
        for mod in ["src.config.settings", "src.startup.validators"]:
            if mod in sys.modules:
                del sys.modules[mod]

        from src.startup.validators import validate_signer_config

        with pytest.warns(UserWarning, match="DO NOT USE IN PRODUCTION"):
            validate_signer_config()

    def test_validate_encryption_config_invalid_dek_size(self, monkeypatch):
        """Test encryption validation fails with invalid DEK size."""
        import sys
        
        monkeypatch.setenv("ENCRYPTION_DEK_BYTES", "15")  # Invalid size
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test")
        monkeypatch.setenv("BASE_RPC_URL", "https://test.rpc")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")

        # Reload modules
        for mod in ["src.config.settings", "src.startup.validators"]:
            if mod in sys.modules:
                del sys.modules[mod]

        from src.startup.validators import validate_encryption_config

        with pytest.raises(RuntimeError, match="Invalid ENCRYPTION_DEK_BYTES"):
            validate_encryption_config()

    def test_run_all_validations(self, monkeypatch):
        """Test all validations run successfully."""
        import sys
        
        monkeypatch.setenv("SIGNER_BACKEND", "kms")
        monkeypatch.setenv("KMS_KEY_ID", "test-key")
        monkeypatch.setenv("ENCRYPTION_DEK_BYTES", "32")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test")
        monkeypatch.setenv("BASE_RPC_URL", "https://test.rpc")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")

        # Reload modules
        for mod in ["src.config.settings", "src.startup.validators"]:
            if mod in sys.modules:
                del sys.modules[mod]

        from src.startup.validators import run_all_validations

        # Should not raise
        run_all_validations()
