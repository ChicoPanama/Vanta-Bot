"""Unit tests for calldata builders (Phase 3)."""

from web3 import Web3


class TestCalldataBuilders:
    """Test ABI encoding for Avantis actions."""

    def test_encode_open(self):
        """Test openPosition calldata encoding."""
        from src.blockchain.avantis.calldata import encode_open
        from src.blockchain.avantis.units import NormalizedOrder

        w3 = Web3()  # No provider needed for encoding
        order = NormalizedOrder("BTC-USD", "LONG", 10_000_000, 2, 20_000_000, 100)

        to_addr, data = encode_open(w3, "0x" + "11" * 20, order, market_id=0)

        # Verify address
        assert to_addr.lower().startswith("0x")
        assert len(to_addr) == 42

        # Verify calldata
        assert isinstance(data, (bytes, bytearray))
        assert len(data) > 4  # Function selector (4 bytes) + args

    def test_encode_close(self):
        """Test closePosition calldata encoding."""
        from src.blockchain.avantis.calldata import encode_close

        w3 = Web3()
        to_addr, data = encode_close(
            w3, "0x" + "22" * 20, market_id=1, reduce_usd_1e6=5_000_000, slippage_bps=50
        )

        # Verify
        assert to_addr.lower().startswith("0x")
        assert isinstance(data, (bytes, bytearray))
        assert len(data) > 4
