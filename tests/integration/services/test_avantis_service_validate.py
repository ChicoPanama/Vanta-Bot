"""Integration tests for AvantisService validation (Phase 3)."""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.database.models import Base


class TestAvantisServiceValidation:
    """Test AvantisService validation logic."""

    @pytest.fixture
    def db_session(self):
        """Create in-memory SQLite session."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        session = Session(engine)
        yield session
        session.close()

    @pytest.fixture
    def mock_w3(self):
        """Mock Web3 instance."""
        w3 = MagicMock()
        w3.eth.chain_id = 8453
        w3.eth.get_block.return_value = {"baseFeePerGas": 1_000_000_000}
        w3.eth.estimate_gas.return_value = 100000
        w3.eth.get_transaction_count.return_value = 5
        return w3

    @pytest.fixture
    def mock_price_agg(self):
        """Mock price aggregator."""
        return MagicMock()

    def test_unknown_market_raises(self, db_session, mock_w3, mock_price_agg):
        """Test that unknown market raises ValueError."""
        from src.blockchain.avantis.service import AvantisService

        service = AvantisService(mock_w3, db_session, mock_price_agg)

        with pytest.raises(ValueError, match="Unknown market"):
            service.open_market(
                user_id=123,
                symbol="UNKNOWN-USD",
                side="LONG",
                collateral_usdc=10.0,
                leverage_x=2,
                slippage_pct=1.0,
            )

    @patch("src.blockchain.signers.factory.get_signer")
    def test_below_min_position_raises(
        self, mock_signer, db_session, mock_w3, mock_price_agg
    ):
        """Test that position below minimum raises ValueError."""
        from src.blockchain.avantis.service import AvantisService

        # Mock signer
        signer = MagicMock()
        signer.address = "0x" + "aa" * 20
        mock_signer.return_value = signer

        service = AvantisService(mock_w3, db_session, mock_price_agg)

        # Try to open tiny position (below 5 USDC min)
        with pytest.raises(ValueError, match="Below min position size"):
            service.open_market(
                user_id=123,
                symbol="BTC-USD",
                side="LONG",
                collateral_usdc=1.0,  # Only 1 USDC
                leverage_x=2,  # = 2 USDC total, below 5 USDC min
                slippage_pct=1.0,
            )

    def test_list_markets(self, db_session, mock_w3, mock_price_agg):
        """Test list_markets returns market info."""
        # Mock price aggregator to return a price
        from src.adapters.price.base import PriceQuote
        from src.blockchain.avantis.service import AvantisService

        mock_price_agg.get_price.return_value = PriceQuote(
            symbol="BTC-USD", price=5000000000000, decimals=8, source="chainlink"
        )

        service = AvantisService(mock_w3, db_session, mock_price_agg)

        markets = service.list_markets()

        # Verify markets are listed
        assert "BTC-USD" in markets
        assert "ETH-USD" in markets

        # Verify market view structure
        btc = markets["BTC-USD"]
        assert btc.symbol == "BTC-USD"
        assert btc.min_position_usd_1e6 == 5_000_000
        assert btc.price == 5000000000000
        assert btc.source == "chainlink"
