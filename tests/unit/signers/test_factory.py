"""Unit tests for signer factory (Phase 1)."""

from unittest.mock import MagicMock

import pytest


class TestSignerFactory:
    """Test signer factory configuration."""

    def test_kms_signer_missing_key_id(self, monkeypatch):
        """Test KMS signer fails without KMS_KEY_ID."""
        from web3 import Web3

        from src.blockchain.signers.factory import get_signer

        monkeypatch.setenv("SIGNER_BACKEND", "kms")
        monkeypatch.delenv("KMS_KEY_ID", raising=False)
        monkeypatch.delenv("AWS_KMS_KEY_ID", raising=False)
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test")
        monkeypatch.setenv("BASE_RPC_URL", "https://test.rpc")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")

        w3 = Web3()

        with pytest.raises(RuntimeError, match="KMS_KEY_ID"):
            get_signer(w3)

    def test_local_signer_missing_private_key(self, monkeypatch):
        """Test local signer fails without PRIVATE_KEY."""
        from web3 import Web3

        from src.blockchain.signers.factory import get_signer

        monkeypatch.setenv("SIGNER_BACKEND", "local")
        monkeypatch.delenv("PRIVATE_KEY", raising=False)
        monkeypatch.delenv("TRADER_PRIVATE_KEY", raising=False)
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test")
        monkeypatch.setenv("BASE_RPC_URL", "https://test.rpc")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")

        w3 = Web3()

        with pytest.raises(RuntimeError, match="PRIVATE_KEY"):
            get_signer(w3)

    def test_local_signer_with_private_key(self, monkeypatch):
        """Test local signer initializes with PRIVATE_KEY."""
        from web3 import Web3

        from src.blockchain.signers.factory import get_signer

        test_key = "0x" + "a" * 64

        monkeypatch.setenv("SIGNER_BACKEND", "local")
        monkeypatch.setenv("PRIVATE_KEY", test_key)
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test")
        monkeypatch.setenv("BASE_RPC_URL", "https://test.rpc")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")

        w3 = Web3()

        with pytest.warns(UserWarning, match="DO NOT USE IN PRODUCTION"):
            signer = get_signer(w3)

        assert signer is not None
        assert hasattr(signer, "address")
        assert hasattr(signer, "sign_tx")

    def test_invalid_signer_backend(self, monkeypatch):
        """Test invalid signer backend raises error."""
        from web3 import Web3

        from src.blockchain.signers.factory import get_signer

        monkeypatch.setenv("SIGNER_BACKEND", "invalid")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test")
        monkeypatch.setenv("BASE_RPC_URL", "https://test.rpc")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")

        w3 = Web3()

        with pytest.raises(RuntimeError, match="Unsupported signer backend"):
            get_signer(w3)
