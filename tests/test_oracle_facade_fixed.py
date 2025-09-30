"""
Fixed Oracle Facade Testing
Properly mocked async providers with correct API alignment
"""

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest

from src.services.oracle import OracleFacade, PriceQuote, create_price_validator


class TestOracleFacadeFixed:
    """Fixed oracle facade testing with proper async mocks."""

    @pytest.fixture
    def mock_primary_provider(self):
        """Mock primary provider with correct async interface."""
        provider = Mock()
        provider.get_price = AsyncMock(
            return_value=PriceQuote(
                price=Decimal("50000.00"),
                timestamp=1234567890,
                source="pyth",
                freshness_sec=5,
                deviation_bps=25,
            )
        )
        return provider

    @pytest.fixture
    def mock_secondary_provider(self):
        """Mock secondary provider with correct async interface."""
        provider = Mock()
        provider.get_price = AsyncMock(
            return_value=PriceQuote(
                price=Decimal("50010.00"),
                timestamp=1234567890,
                source="chainlink",
                freshness_sec=8,
                deviation_bps=30,
            )
        )
        return provider

    @pytest.fixture
    def oracle_facade(self, mock_primary_provider, mock_secondary_provider):
        """Create oracle facade with mocked providers."""
        return OracleFacade(
            primary=mock_primary_provider, secondary=mock_secondary_provider
        )

    @pytest.mark.asyncio
    async def test_healthy_dual_feed_operation(
        self, oracle_facade, mock_primary_provider, mock_secondary_provider
    ):
        """Test oracle facade with healthy dual feeds."""
        # Test with healthy feeds (small deviation)
        result = await oracle_facade.get_price("BTC/USD")

        # Verify result
        assert result.price == Decimal("50000.00")
        assert result.deviation_bps <= 50
        assert result.freshness_sec <= 10

        # Verify primary provider was called
        mock_primary_provider.get_price.assert_called_once_with("BTC", 5, 50)

        # Secondary provider may or may not be called depending on implementation
        # This is implementation-specific behavior

    @pytest.mark.asyncio
    async def test_primary_failure_fallback(
        self, oracle_facade, mock_primary_provider, mock_secondary_provider
    ):
        """Test fallback to secondary when primary fails."""
        # Make primary fail
        mock_primary_provider.get_price.side_effect = Exception("Primary unavailable")

        # Should fallback to secondary
        result = await oracle_facade.get_price("BTC/USD")

        assert result.price == Decimal("50010.00")
        assert result.source == "chainlink"

        # Verify both providers were called
        mock_primary_provider.get_price.assert_called_once_with("BTC", 5, 50)
        mock_secondary_provider.get_price.assert_called_once_with("BTC", 5, 50)

    @pytest.mark.asyncio
    async def test_high_deviation_rejection(
        self, oracle_facade, mock_primary_provider, mock_secondary_provider
    ):
        """Test rejection when feeds have high deviation."""
        # Set high deviation between providers
        mock_primary_provider.get_price.return_value = PriceQuote(
            price=Decimal("50000.00"),
            timestamp=1234567890,
            source="pyth",
            freshness_sec=5,
            deviation_bps=25,
        )
        mock_secondary_provider.get_price.return_value = PriceQuote(
            price=Decimal("60000.00"),  # 20% deviation
            timestamp=1234567890,
            source="chainlink",
            freshness_sec=8,
            deviation_bps=30,
        )

        # Should reject due to high deviation
        with pytest.raises(ValueError, match="Price deviation too high"):
            await oracle_facade.get_price("BTC/USD")

    @pytest.mark.asyncio
    async def test_stale_price_rejection(
        self, oracle_facade, mock_primary_provider, mock_secondary_provider
    ):
        """Test rejection of stale prices."""
        # Set stale price
        mock_primary_provider.get_price.return_value = PriceQuote(
            price=Decimal("50000.00"),
            timestamp=1234567890,
            source="pyth",
            freshness_sec=120,  # 2 minutes old
            deviation_bps=25,
        )
        mock_secondary_provider.get_price.return_value = PriceQuote(
            price=Decimal("50010.00"),
            timestamp=1234567890,
            source="chainlink",
            freshness_sec=8,
            deviation_bps=30,
        )

        # Should reject due to stale price
        with pytest.raises(ValueError, match="Price too stale"):
            await oracle_facade.get_price("BTC/USD")

    @pytest.mark.asyncio
    async def test_symbol_normalization(
        self, oracle_facade, mock_primary_provider, mock_secondary_provider
    ):
        """Test symbol normalization in oracle facade."""
        # Test with UI format symbol
        await oracle_facade.get_price("BTC/USD")

        # Verify canonical symbol was used
        mock_primary_provider.get_price.assert_called_once_with("BTC", 5, 50)

        # Test with canonical symbol
        await oracle_facade.get_price("BTC")

        # Verify canonical symbol was used
        assert mock_primary_provider.get_price.call_count == 2

    @pytest.mark.asyncio
    async def test_environment_thresholds(self):
        """Test environment variable threshold configuration."""
        import os

        # Set custom thresholds
        os.environ["ORACLE_MAX_DEVIATION_BPS"] = "100"
        os.environ["ORACLE_MAX_AGE_S"] = "60"

        try:
            validator = create_price_validator()
            assert validator.max_deviation_bps == 100
            assert validator.max_freshness_sec == 60
        finally:
            # Clean up
            os.environ.pop("ORACLE_MAX_DEVIATION_BPS", None)
            os.environ.pop("ORACLE_MAX_AGE_S", None)

    @pytest.mark.asyncio
    async def test_concurrent_price_requests(
        self, oracle_facade, mock_primary_provider, mock_secondary_provider
    ):
        """Test concurrent price requests."""
        # Make multiple concurrent requests
        tasks = [
            oracle_facade.get_price("BTC/USD"),
            oracle_facade.get_price("ETH/USD"),
            oracle_facade.get_price("SOL/USD"),
        ]

        results = await asyncio.gather(*tasks)

        # Verify all requests succeeded
        assert len(results) == 3
        for result in results:
            assert result.price > 0
            assert result.deviation_bps <= 50

        # Verify providers were called for each request
        assert mock_primary_provider.get_price.call_count == 3

    @pytest.mark.asyncio
    async def test_provider_timeout_handling(
        self, mock_primary_provider, mock_secondary_provider
    ):
        """Test timeout handling in oracle facade."""
        # Make primary timeout
        mock_primary_provider.get_price.side_effect = asyncio.TimeoutError(
            "Request timeout"
        )

        facade = OracleFacade(
            primary=mock_primary_provider, secondary=mock_secondary_provider
        )

        # Should fallback to secondary
        result = await facade.get_price("BTC/USD")

        assert result.price == Decimal("50010.00")
        assert result.source == "chainlink"

    @pytest.mark.asyncio
    async def test_both_providers_fail(
        self, mock_primary_provider, mock_secondary_provider
    ):
        """Test behavior when both providers fail."""
        # Make both providers fail
        mock_primary_provider.get_price.side_effect = Exception("Primary unavailable")
        mock_secondary_provider.get_price.side_effect = Exception(
            "Secondary unavailable"
        )

        facade = OracleFacade(
            primary=mock_primary_provider, secondary=mock_secondary_provider
        )

        # Should raise exception
        with pytest.raises(Exception, match="Both oracle providers failed"):
            await facade.get_price("BTC/USD")

    @pytest.mark.asyncio
    async def test_price_deviation_calculation(
        self, oracle_facade, mock_primary_provider, mock_secondary_provider
    ):
        """Test price deviation calculation between providers."""
        # Set specific prices for deviation calculation
        mock_primary_provider.get_price.return_value = PriceQuote(
            price=Decimal("50000.00"),
            timestamp=1234567890,
            source="pyth",
            freshness_sec=5,
            deviation_bps=25,
        )
        mock_secondary_provider.get_price.return_value = PriceQuote(
            price=Decimal("50100.00"),  # 0.2% deviation
            timestamp=1234567890,
            source="chainlink",
            freshness_sec=8,
            deviation_bps=30,
        )

        result = await oracle_facade.get_price("BTC/USD")

        # Should accept small deviation
        assert result.price == Decimal("50000.00")
        assert result.deviation_bps <= 50

    @pytest.mark.asyncio
    async def test_unsupported_symbol_handling(
        self, oracle_facade, mock_primary_provider, mock_secondary_provider
    ):
        """Test handling of unsupported symbols."""
        # Make providers raise unsupported symbol error
        mock_primary_provider.get_price.side_effect = ValueError(
            "Unsupported symbol: UNKNOWN"
        )
        mock_secondary_provider.get_price.side_effect = ValueError(
            "Unsupported symbol: UNKNOWN"
        )

        # Should raise exception
        with pytest.raises(ValueError, match="Unsupported symbol"):
            await oracle_facade.get_price("UNKNOWN/USD")
