"""Integration tests for transaction orchestrator timeout handling (Phase 2)."""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from web3.exceptions import TransactionNotFound

from src.database.models import Base


class TestOrchestratorTimeout:
    """Test orchestrator timeout and RBF behavior."""

    @pytest.fixture
    def db_session(self):
        """Create in-memory SQLite session."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        session = Session(engine)
        yield session
        session.close()

    @pytest.fixture
    def mock_web3_timeout(self):
        """Mock Web3 that times out on receipts."""
        w3 = MagicMock()
        w3.eth.chain_id = 8453
        w3.eth.get_block.return_value = {"baseFeePerGas": 1_000_000_000}
        w3.eth.estimate_gas.return_value = 100000
        w3.eth.get_transaction_count.return_value = 5

        # Return different tx hashes for each send (RBF creates new hashes)
        tx_counter = {"count": 0}

        def get_hash():
            tx_counter["count"] += 1
            return "0x" + f"{tx_counter['count']:064x}"

        w3.eth.send_raw_transaction.return_value = MagicMock()
        w3.eth.send_raw_transaction.return_value.hex = get_hash

        # Always raise TransactionNotFound (simulates timeout)
        w3.eth.get_transaction_receipt.side_effect = TransactionNotFound(
            "Transaction not found"
        )
        return w3

    @patch("src.blockchain.signers.factory.get_signer")
    @patch("time.sleep", return_value=None)  # Speed up test
    def test_timeout_triggers_rbf(
        self, mock_sleep, mock_get_signer, db_session, mock_web3_timeout
    ):
        """Test that timeout triggers RBF replacement."""
        from src.blockchain.tx.orchestrator import TxOrchestrator

        mock_signer = MagicMock()
        mock_signer.address = "0x" + "bb" * 20
        mock_signer.sign_tx.return_value = b"\x12\x34"
        mock_get_signer.return_value = mock_signer

        orch = TxOrchestrator(
            mock_web3_timeout, db_session, rbf_attempts=2, rbf_bump_multiplier=1.15
        )

        # Should raise RuntimeError after exhausting RBF attempts
        with pytest.raises(RuntimeError, match="timed out"):
            orch.execute(
                intent_key="timeout:test",
                to="0x" + "cc" * 20,
                data=b"",
                confirmations=0,
            )

        # Should have attempted multiple sends (original + RBF retries)
        # Original + 1 RBF = 2 total sends
        assert mock_web3_timeout.eth.send_raw_transaction.call_count >= 2
