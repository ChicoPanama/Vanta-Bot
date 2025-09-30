"""Tests for transaction pipeline components."""

from unittest.mock import Mock, patch

import pytest

from src.blockchain.tx.builder import TxBuilder
from src.blockchain.tx.gas_policy import GasPolicy
from src.blockchain.tx.nonce_manager import NonceManager
from src.blockchain.tx.sender import TxSender


class TestNonceManager:
    """Test nonce management."""

    def test_reserve_nonce(self):
        """Test nonce reservation."""
        mock_redis = Mock()
        mock_web3 = Mock()
        mock_web3.eth.get_transaction_count.return_value = 5

        nonce_manager = NonceManager(mock_redis, mock_web3)

        with nonce_manager.reserve("0x123") as nonce:
            assert nonce == 5
            mock_redis.set.assert_called_once()

    def test_nonce_increment(self):
        """Test that nonce increments on each reservation."""
        mock_redis = Mock()
        mock_web3 = Mock()
        mock_web3.eth.get_transaction_count.return_value = 5

        nonce_manager = NonceManager(mock_redis, mock_web3)

        # First reservation
        with nonce_manager.reserve("0x123") as nonce1:
            assert nonce1 == 5

        # Second reservation should increment
        mock_redis.get.return_value = b"6"  # Cached nonce
        with nonce_manager.reserve("0x123") as nonce2:
            assert nonce2 == 6


class TestGasPolicy:
    """Test gas policy."""

    def test_gas_quote(self):
        """Test gas price quoting."""
        mock_web3 = Mock()
        mock_web3.eth.gas_price = 20000000000  # 20 Gwei

        gas_policy = GasPolicy()
        max_fee, max_priority = gas_policy.quote(mock_web3)

        assert max_fee > 0
        assert max_priority > 0
        assert max_fee >= max_priority

    def test_gas_quote_with_caps(self):
        """Test gas price quoting with caps."""
        mock_web3 = Mock()
        mock_web3.eth.gas_price = 200000000000  # 200 Gwei (very high)

        gas_policy = GasPolicy(max_fee_cap_gwei=150)  # 150 Gwei cap
        max_fee, max_priority = gas_policy.quote(mock_web3)

        # Should be capped at 150 Gwei
        assert max_fee <= 150 * 1e9

    def test_fee_bump(self):
        """Test fee bumping for retries."""
        gas_policy = GasPolicy()
        original_fee = 10000000000  # 10 Gwei

        bumped_fee = gas_policy.bump_fee(original_fee, bump_percent=0.15)

        assert bumped_fee > original_fee
        assert bumped_fee == int(original_fee * 1.15)


class TestTxBuilder:
    """Test transaction builder."""

    def test_build_transaction(self):
        """Test transaction building."""
        mock_web3 = Mock()
        mock_web3.eth.chain_id = 8453

        builder = TxBuilder(mock_web3, 8453)

        tx = builder.build(
            from_addr="0x123",
            to="0x456",
            data=b"0x1234",
            value=1000000000000000000,  # 1 ETH
            gas=21000,
            nonce=5,
            max_fee=20000000000,
            max_priority=2000000000,
        )

        assert tx["chainId"] == 8453
        assert tx["from"] == "0x123"
        assert tx["to"] == "0x456"
        assert tx["data"] == b"0x1234"
        assert tx["value"] == 1000000000000000000
        assert tx["gas"] == 21000
        assert tx["nonce"] == 5
        assert tx["maxFeePerGas"] == 20000000000
        assert tx["maxPriorityFeePerGas"] == 2000000000
        assert tx["type"] == 2  # EIP-1559

    def test_sign_transaction(self):
        """Test transaction signing."""
        mock_web3 = Mock()
        builder = TxBuilder(mock_web3, 8453)

        tx = {
            "chainId": 8453,
            "from": "0x123",
            "to": "0x456",
            "data": b"0x1234",
            "value": 0,
            "gas": 21000,
            "nonce": 5,
            "maxFeePerGas": 20000000000,
            "maxPriorityFeePerGas": 2000000000,
            "type": 2,
        }

        # Mock private key
        private_key = "0x" + "1" * 64

        with patch("eth_account.Account.from_key") as mock_account:
            mock_signer = Mock()
            mock_signer.sign_transaction.return_value.rawTransaction = b"signed_tx"
            mock_account.return_value = mock_signer

            signed_tx = builder.sign(tx, private_key)

            assert signed_tx == b"signed_tx"
            mock_signer.sign_transaction.assert_called_once_with(tx)

    def test_estimate_gas(self):
        """Test gas estimation."""
        mock_web3 = Mock()
        mock_web3.eth.estimate_gas.return_value = 21000

        builder = TxBuilder(mock_web3, 8453)

        tx_params = {"from": "0x123", "to": "0x456", "data": b"0x1234", "value": 0}

        gas_estimate = builder.estimate_gas(tx_params)

        assert gas_estimate == 25200  # 21000 * 1.2 (20% buffer)
        mock_web3.eth.estimate_gas.assert_called_once_with(tx_params)


class TestTxSender:
    """Test transaction sender."""

    def test_send_with_retry_success(self):
        """Test successful transaction sending."""
        mock_web3 = Mock()
        mock_web3.eth.send_raw_transaction.return_value = b"0x1234567890abcdef"

        mock_tx_repo = Mock()
        mock_tx_repo.get_by_request_id.return_value = None

        sender = TxSender(mock_web3, mock_tx_repo)

        tx_hash = sender.send_with_retry(b"raw_tx", "request_123")

        assert tx_hash == "0x1234567890abcdef"
        mock_tx_repo.record_sent.assert_called_once_with(
            "request_123", "0x1234567890abcdef"
        )

    def test_send_with_retry_idempotency(self):
        """Test idempotency - don't send if already sent."""
        mock_web3 = Mock()
        mock_tx_repo = Mock()
        mock_tx_repo.get_by_request_id.return_value = Mock(tx_hash="0xexisting")

        sender = TxSender(mock_web3, mock_tx_repo)

        tx_hash = sender.send_with_retry(b"raw_tx", "request_123")

        assert tx_hash == "0xexisting"
        mock_web3.eth.send_raw_transaction.assert_not_called()

    def test_send_with_retry_failure(self):
        """Test retry logic on failure."""
        mock_web3 = Mock()
        mock_web3.eth.send_raw_transaction.side_effect = Exception("RPC error")

        mock_tx_repo = Mock()
        mock_tx_repo.get_by_request_id.return_value = None

        sender = TxSender(mock_web3, mock_tx_repo)

        with pytest.raises(Exception, match="RPC error"):
            sender.send_with_retry(b"raw_tx", "request_123")

        # Should have tried 4 times (1 initial + 3 retries)
        assert mock_web3.eth.send_raw_transaction.call_count == 4

    def test_send_with_retry_success_after_failure(self):
        """Test successful send after initial failure."""
        mock_web3 = Mock()
        mock_web3.eth.send_raw_transaction.side_effect = [
            Exception("RPC error"),
            Exception("RPC error"),
            b"0x1234567890abcdef",  # Success on third try
        ]

        mock_tx_repo = Mock()
        mock_tx_repo.get_by_request_id.return_value = None

        sender = TxSender(mock_web3, mock_tx_repo)

        tx_hash = sender.send_with_retry(b"raw_tx", "request_123")

        assert tx_hash == "0x1234567890abcdef"
        assert mock_web3.eth.send_raw_transaction.call_count == 3
