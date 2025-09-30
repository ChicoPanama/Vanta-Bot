"""Integration tests for transaction orchestrator idempotency (Phase 2)."""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from web3 import Web3

from src.database.models import Base, TxIntent, TxSend


class TestOrchestratorIdempotency:
    """Test orchestrator idempotency behavior."""

    @pytest.fixture
    def db_session(self):
        """Create in-memory SQLite session."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        session = Session(engine)
        yield session
        session.close()

    @pytest.fixture
    def mock_web3(self):
        """Mock Web3 instance."""
        w3 = MagicMock()
        w3.eth.chain_id = 8453
        w3.eth.get_block.return_value = {"baseFeePerGas": 1_000_000_000}
        w3.eth.estimate_gas.return_value = 100000
        w3.eth.get_transaction_count.return_value = 5
        # Mock send_raw_transaction to return a hash
        w3.eth.send_raw_transaction.return_value = MagicMock(
            hex=lambda: "0x" + "aa" * 32
        )
        # Mock receipt
        receipt = MagicMock()
        receipt.transactionHash.hex.return_value = "0x" + "aa" * 32
        receipt.status = 1
        receipt.blockNumber = 1000
        receipt.gasUsed = 90000
        receipt.effectiveGasPrice = 2_000_000_000
        w3.eth.get_transaction_receipt.return_value = receipt
        return w3

    @patch("src.blockchain.signers.factory.get_signer")
    def test_execute_idempotent(self, mock_get_signer, db_session, mock_web3):
        """Test that calling execute twice with same intent_key returns same hash."""
        from src.blockchain.tx.orchestrator import TxOrchestrator

        # Mock signer
        mock_signer = MagicMock()
        mock_signer.address = "0x" + "bb" * 20
        mock_signer.sign_tx.return_value = b"\x12\x34\x56\x78"
        mock_get_signer.return_value = mock_signer

        orch = TxOrchestrator(mock_web3, db_session)

        intent_key = "test:123:unique"
        to_addr = "0x" + "cc" * 20
        data = b"\xab\xcd"

        # First execution
        hash1 = orch.execute(
            intent_key=intent_key, to=to_addr, data=data, confirmations=0
        )

        # Verify transaction was sent
        assert hash1 == "0x" + "aa" * 32
        assert mock_web3.eth.send_raw_transaction.call_count == 1

        # Second execution with same intent_key
        hash2 = orch.execute(
            intent_key=intent_key, to=to_addr, data=data, confirmations=0
        )

        # Should return same hash without sending again
        assert hash2 == hash1
        # send_raw_transaction should still only have been called once
        assert mock_web3.eth.send_raw_transaction.call_count == 1

        # Verify only one send record exists
        sends = db_session.query(TxSend).all()
        assert len(sends) == 1

    @patch("src.blockchain.signers.factory.get_signer")
    def test_intent_status_transitions(self, mock_get_signer, db_session, mock_web3):
        """Test intent status transitions through lifecycle."""
        from src.blockchain.tx.orchestrator import TxOrchestrator

        # Mock signer
        mock_signer = MagicMock()
        mock_signer.address = "0x" + "bb" * 20
        mock_signer.sign_tx.return_value = b"\x12\x34"
        mock_get_signer.return_value = mock_signer

        orch = TxOrchestrator(mock_web3, db_session)

        intent_key = "test:456:status-test"

        # Execute
        orch.execute(
            intent_key=intent_key,
            to="0x" + "dd" * 20,
            data=b"",
            confirmations=0,
        )

        # Check intent status progression
        intent = db_session.query(TxIntent).filter_by(intent_key=intent_key).one()
        assert intent.status == "MINED"  # After successful receipt

    @patch("src.blockchain.signers.factory.get_signer")
    def test_different_intents_send_separately(
        self, mock_get_signer, db_session, mock_web3
    ):
        """Test that different intent keys result in separate transactions."""
        from src.blockchain.tx.orchestrator import TxOrchestrator

        mock_signer = MagicMock()
        mock_signer.address = "0x" + "bb" * 20
        mock_signer.sign_tx.return_value = b"\x12\x34"
        mock_get_signer.return_value = mock_signer

        # Return different hashes for each send
        hashes = [("0x" + "aa" * 32), ("0x" + "bb" * 32)]
        mock_web3.eth.send_raw_transaction.side_effect = [
            MagicMock(hex=lambda h=h: h) for h in hashes
        ]

        # Different receipts
        def make_receipt(h):
            r = MagicMock()
            r.transactionHash.hex.return_value = h
            r.status = 1
            r.blockNumber = 1000
            r.gasUsed = 90000
            r.effectiveGasPrice = 2_000_000_000
            return r

        mock_web3.eth.get_transaction_receipt.side_effect = [
            make_receipt(h) for h in hashes
        ]

        orch = TxOrchestrator(mock_web3, db_session)

        # Execute with different intent keys
        hash1 = orch.execute("intent:1", to="0x" + "cc" * 20, data=b"", confirmations=0)
        hash2 = orch.execute("intent:2", to="0x" + "cc" * 20, data=b"", confirmations=0)

        # Should be different
        assert hash1 != hash2
        # Should have sent twice
        assert mock_web3.eth.send_raw_transaction.call_count == 2
