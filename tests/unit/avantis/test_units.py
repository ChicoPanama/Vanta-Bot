"""Unit tests for unit normalization (Phase 3)."""


class TestUnitNormalization:
    """Test single-scaling unit normalization."""

    def test_to_normalized_scaling(self) -> None:
        """Test float to integer conversion with correct scaling."""
        from src.blockchain.avantis.units import to_normalized

        order = to_normalized(
            "BTC-USD", "LONG", collateral_usdc=10.0, leverage_x=2, slippage_pct=1.0
        )

        # Verify single-scaling
        assert order.collateral_usdc == 10_000_000  # 10 USDC in 1e6
        assert order.size_usd == 20_000_000  # 10 * 2 leverage in 1e6
        assert order.slippage_bps == 100  # 1% = 100 bps
        assert order.symbol == "BTC-USD"
        assert order.side == "LONG"

    def test_to_normalized_uppercase(self) -> None:
        """Test symbol and side are uppercased."""
        from src.blockchain.avantis.units import to_normalized

        order = to_normalized("btc-usd", "long", 5.0, 10, 0.5)

        assert order.symbol == "BTC-USD"
        assert order.side == "LONG"

    def test_to_normalized_fractional_usdc(self) -> None:
        """Test fractional USDC amounts."""
        from src.blockchain.avantis.units import to_normalized

        order = to_normalized("ETH-USD", "SHORT", 7.5, 3, 1.5)

        assert order.collateral_usdc == 7_500_000  # 7.5 USDC
        assert order.size_usd == 22_500_000  # 7.5 * 3
        assert order.slippage_bps == 150  # 1.5% = 150 bps
