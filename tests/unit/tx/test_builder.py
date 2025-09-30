"""Unit tests for transaction builder (Phase 2)."""

from unittest.mock import MagicMock

import pytest
from web3 import Web3


class TestTxBuilder:
    """Test transaction builder."""

    def test_build_tx_params_produces_type2(self):
        """Test builder produces EIP-1559 (type 2) transactions."""
        from src.blockchain.tx.builder import TxBuilder
        from src.blockchain.tx.gas_policy import GasPolicy

        # Mock Web3
        w3 = MagicMock()
        w3.eth.chain_id = 8453
        w3.eth.estimate_gas.return_value = 100000
        w3.eth.get_block.return_value = {"baseFeePerGas": 1_000_000_000}

        builder = TxBuilder(w3, 8453, GasPolicy())

        tx = builder.build_tx_params(
            to="0x" + "11" * 20,
            data=b"\x12\x34",
            from_addr="0x" + "aa" * 20,
            value=0,
        )

        # Verify EIP-1559 fields
        assert tx["type"] == 2
        assert "maxFeePerGas" in tx
        assert "maxPriorityFeePerGas" in tx
        assert tx["chainId"] == 8453
        assert "gas" in tx
        assert tx["gas"] > 100000  # Should include buffer

    def test_build_tx_params_with_gas_hint(self):
        """Test builder respects gas limit hint."""
        from src.blockchain.tx.builder import TxBuilder

        w3 = MagicMock()
        w3.eth.chain_id = 8453
        w3.eth.get_block.return_value = {"baseFeePerGas": 1_000_000_000}

        builder = TxBuilder(w3, 8453)

        tx = builder.build_tx_params(
            to="0x" + "11" * 20,
            data=b"",
            from_addr="0x" + "aa" * 20,
            gas_limit_hint=200000,
        )

        # Should use hint, not estimate
        assert tx["gas"] == 200000
        # estimate_gas should not have been called
        assert not w3.eth.estimate_gas.called

    def test_build_tx_checksums_addresses(self):
        """Test builder checksums addresses."""
        from src.blockchain.tx.builder import TxBuilder

        w3 = Web3()  # Real Web3 for checksum
        w3.eth = MagicMock()
        w3.eth.chain_id = 8453
        w3.eth.get_block.return_value = {"baseFeePerGas": 1_000_000_000}
        w3.eth.estimate_gas.return_value = 100000

        builder = TxBuilder(w3, 8453)

        # Use lowercase addresses
        tx = builder.build_tx_params(
            to="0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
            data=b"",
            from_addr="0x1234567890123456789012345678901234567890",
        )

        # Should be checksummed
        assert tx["to"].startswith("0x")
        assert tx["from"].startswith("0x")
        # At least some uppercase chars in checksummed address
        assert tx["to"] != tx["to"].lower() or tx["from"] != tx["from"].lower()
