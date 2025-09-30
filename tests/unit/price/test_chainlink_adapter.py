"""Unit tests for Chainlink adapter (Phase 3)."""

from unittest.mock import MagicMock

from web3 import Web3


class TestChainlinkAdapter:
    """Test Chainlink price adapter."""

    def test_get_price_success(self):
        """Test successful price retrieval."""
        from src.adapters.price.chainlink_adapter import ChainlinkAdapter

        # Mock Web3
        w3 = MagicMock()
        mock_contract = MagicMock()
        mock_contract.functions.decimals().call.return_value = 8
        mock_contract.functions.latestRoundData().call.return_value = (
            1,  # roundId
            5000000000000,  # answer (50000 with 8 decimals)
            1000000,  # startedAt
            1000000,  # updatedAt
            1,  # answeredInRound
        )
        w3.eth.contract.return_value = mock_contract

        adapter = ChainlinkAdapter(
            w3, {"BTC-USD": "0x64c911996D3c6aC71f9b455B1E8E7266BcbD848F"}
        )

        quote = adapter.get_price("BTC-USD")

        assert quote is not None
        assert quote.symbol == "BTC-USD"
        assert quote.price == 5000000000000
        assert quote.decimals == 8
        assert quote.source == "chainlink"

    def test_get_price_unknown_symbol(self):
        """Test None returned for unknown symbol."""
        from src.adapters.price.chainlink_adapter import ChainlinkAdapter

        w3 = MagicMock()
        adapter = ChainlinkAdapter(w3, {"BTC-USD": "0x" + "aa" * 20})

        quote = adapter.get_price("UNKNOWN-USD")

        assert quote is None

    def test_get_price_invalid_answer(self):
        """Test None returned for invalid (negative) price."""
        from src.adapters.price.chainlink_adapter import ChainlinkAdapter

        w3 = MagicMock()
        mock_contract = MagicMock()
        mock_contract.functions.decimals().call.return_value = 8
        mock_contract.functions.latestRoundData().call.return_value = (
            1,
            -1,  # Invalid negative price
            1000000,
            1000000,
            1,
        )
        w3.eth.contract.return_value = mock_contract

        adapter = ChainlinkAdapter(w3, {"BTC-USD": "0x" + "aa" * 20})

        quote = adapter.get_price("BTC-USD")

        assert quote is None
