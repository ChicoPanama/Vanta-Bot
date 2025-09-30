"""Unit tests for EIP-1559 gas policy (Phase 2)."""

from unittest.mock import MagicMock

import pytest


class TestGasPolicy:
    """Test EIP-1559 gas policy."""

    def test_quote_with_base_fee(self):
        """Test gas quote with baseFeePerGas present."""
        from src.blockchain.tx.gas_policy import GasPolicy

        # Mock Web3 client
        w3 = MagicMock()
        w3.eth.get_block.return_value = {
            "baseFeePerGas": 1_000_000_000,  # 1 Gwei
        }

        policy = GasPolicy(
            max_fee_cap_gwei=150, max_priority_gwei=2, surge_multiplier=1.2
        )
        max_fee, priority = policy.quote(w3)

        # max_fee = (base + priority) * surge = (1 + 2) * 1.2 = 3.6 Gwei
        assert max_fee == int(3.6 * 1e9)
        assert priority == 2_000_000_000  # 2 Gwei

    def test_quote_without_base_fee_fallback(self):
        """Test fallback when baseFeePerGas is None."""
        from src.blockchain.tx.gas_policy import GasPolicy

        # Mock Web3 client without baseFeePerGas
        w3 = MagicMock()
        w3.eth.get_block.return_value = {}
        w3.eth.gas_price = 10_000_000_000  # 10 Gwei

        policy = GasPolicy()
        max_fee, priority = policy.quote(w3)

        # Should fall back to gas_price * 1.2
        assert max_fee == int(10 * 1.2 * 1e9)
        assert priority == int(10 * 1.2 * 0.1 * 1e9)

    def test_fee_cap_enforced(self):
        """Test that max fee cap is enforced."""
        from src.blockchain.tx.gas_policy import GasPolicy

        # Mock very high base fee
        w3 = MagicMock()
        w3.eth.get_block.return_value = {
            "baseFeePerGas": 200_000_000_000,  # 200 Gwei (very high)
        }

        policy = GasPolicy(max_fee_cap_gwei=150)  # Cap at 150 Gwei
        max_fee, priority = policy.quote(w3)

        # Should be capped at 150 Gwei
        assert max_fee == 150_000_000_000

    def test_bump_fee(self):
        """Test fee bumping for RBF."""
        from src.blockchain.tx.gas_policy import GasPolicy

        policy = GasPolicy(max_fee_cap_gwei=150)

        current_fee = 10_000_000_000  # 10 Gwei
        bumped = policy.bump_fee(current_fee, bump_percent=0.15)

        # Should be 10 * 1.15 = 11.5 Gwei
        assert bumped == int(10 * 1.15 * 1e9)

    def test_bump_fee_respects_cap(self):
        """Test fee bump respects max cap."""
        from src.blockchain.tx.gas_policy import GasPolicy

        policy = GasPolicy(max_fee_cap_gwei=150)

        current_fee = 140_000_000_000  # 140 Gwei
        bumped = policy.bump_fee(current_fee, bump_percent=0.20)

        # Would be 168 Gwei, but capped at 150
        assert bumped == 150_000_000_000
