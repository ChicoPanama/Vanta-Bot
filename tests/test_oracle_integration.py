"""Integration tests for oracle facade and execution mode manager."""

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.services.copy_trading.execution_mode import ExecutionMode, ExecutionModeManager
from src.services.oracle import OracleFacade, PriceQuote, create_price_validator
from src.services.oracle_providers.chainlink import ChainlinkOracle
from src.services.oracle_providers.pyth import PythOracle


class TestOracleFacadeIntegration:
    """Integration tests for oracle facade."""

    @pytest.fixture
    async def mock_pyth_oracle(self):
        """Mock Pyth oracle with async get_price and realistic quote."""
        oracle = Mock(spec=PythOracle)
        oracle.get_price = AsyncMock(
            return_value=PriceQuote(
                price=Decimal("50000.00"),
                timestamp=1234567890,
                source="pyth",
                freshness_sec=5,
                deviation_bps=25,
            )
        )
        return oracle

    @pytest.fixture
    async def mock_chainlink_oracle(self):
        """Mock Chainlink oracle with async get_price and realistic quote."""
        oracle = Mock(spec=ChainlinkOracle)
        oracle.get_price = AsyncMock(
            return_value=PriceQuote(
                price=Decimal("50010.00"),
                timestamp=1234567890,
                source="chainlink",
                freshness_sec=8,
                deviation_bps=30,
            )
        )
        return oracle

    @pytest.mark.asyncio
    async def test_dual_feed_deviation_gating(
        self, mock_pyth_oracle, mock_chainlink_oracle
    ):
        """Test dual-feed deviation gating with healthy feeds."""
        # Create oracle facade with mock providers
        facade = OracleFacade(primary=mock_pyth_oracle, secondary=mock_chainlink_oracle)

        # Test with healthy feeds (small deviation)
        result = await facade.get_price("BTC/USD")

        assert result.price == Decimal("50000.00")
        assert result.deviation_bps <= 50  # Within threshold
        mock_pyth_oracle.get_price.assert_called_once()
        mock_chainlink_oracle.get_price.assert_called_once()

    @pytest.mark.asyncio
    async def test_secondary_fallback_on_primary_failure(
        self, mock_pyth_oracle, mock_chainlink_oracle
    ):
        """Test fallback to secondary when primary fails."""
        # Make primary fail
        mock_pyth_oracle.get_price.side_effect = Exception("Pyth unavailable")

        facade = OracleFacade(primary=mock_pyth_oracle, secondary=mock_chainlink_oracle)

        # Should fallback to secondary
        result = await facade.get_price("BTC/USD")

        assert result.price == Decimal("50010.00")
        mock_pyth_oracle.get_price.assert_called_once()
        mock_chainlink_oracle.get_price.assert_called_once()

    @pytest.mark.asyncio
    async def test_high_deviation_rejection(
        self, mock_pyth_oracle, mock_chainlink_oracle
    ):
        """Test rejection when feeds have high deviation."""
        # Set high deviation
        mock_pyth_oracle.get_price.return_value = PriceQuote(
            price=Decimal("50000.00"),
            timestamp=1234567890,
            source="pyth",
            deviation_bps=25,
            freshness_sec=5,
        )
        mock_chainlink_oracle.get_price.return_value = PriceQuote(
            price=Decimal("60000.00"),  # 20% deviation
            timestamp=1234567890,
            source="chainlink",
            deviation_bps=30,
            freshness_sec=8,
        )

        facade = OracleFacade(primary=mock_pyth_oracle, secondary=mock_chainlink_oracle)

        # Should reject due to high deviation
        with pytest.raises(ValueError, match="Price deviation too high"):
            await facade.get_price("BTC/USD")

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


class TestExecutionModeManagerIntegration:
    """Integration tests for execution mode manager."""

    @pytest.fixture
    def execution_manager(self):
        """Create execution mode manager with in-memory Redis stub."""

        class InMemoryRedis:
            def __init__(self):
                self.store = {}

            def ping(self):
                return True

            def get(self, key):
                v = self.store.get(key)
                if v is None:
                    return None
                return v

            def set(self, key, value):
                self.store[key] = value
                return True

        stub = InMemoryRedis()
        # Provide stub to manager
        return ExecutionModeManager(redis_client=stub)

    def test_initialization_from_environment(self, execution_manager):
        """Test initialization from environment variables."""

        # Test default mode
        assert execution_manager.mode == ExecutionMode.DRY

        # Test emergency stop state
        assert not execution_manager.is_emergency_stopped

    @pytest.mark.asyncio
    async def test_redis_persistence(self, execution_manager):
        """Test Redis persistence of execution mode."""
        # Set mode to LIVE
        execution_manager.set_mode(ExecutionMode.LIVE)
        assert execution_manager.mode == ExecutionMode.LIVE

        # Create new manager instance (simulates different process)
        # Use same stub to simulate cross-process persistence
        new_manager = ExecutionModeManager(redis_client=execution_manager.redis)

        # Should load from Redis
        new_manager.refresh_from_redis()
        assert new_manager.mode == ExecutionMode.LIVE

    @pytest.mark.asyncio
    async def test_emergency_stop_persistence(self, execution_manager):
        """Test emergency stop persistence across processes."""
        # Set emergency stop
        execution_manager.set_emergency_stop(True)
        assert execution_manager.is_emergency_stopped

        # Create new manager instance
        new_manager = ExecutionModeManager(redis_client=execution_manager.redis)
        new_manager.refresh_from_redis()

        # Should reflect emergency stop
        assert new_manager.is_emergency_stopped

    def test_health_metrics(self, execution_manager):
        """Test health metrics generation."""
        metrics = execution_manager.get_health_metrics()
        assert "execution_mode" in metrics
        assert "emergency_stop" in metrics
        assert "redis_persistence" in metrics
        assert "timestamp" in metrics

    def test_execution_context(self, execution_manager):
        """Test execution context generation."""
        context = execution_manager.get_execution_context()
        assert "mode" in context
        assert "emergency_stop" in context
        assert "can_execute" in context
        assert "redis_connected" in context


class TestOracleProviderIntegration:
    """Integration tests for oracle providers."""

    @pytest.mark.asyncio
    async def test_pyth_expo_scaling(self):
        """Test Pyth expo scaling calculation."""
        # Mock Pyth response with expo scaling
        import time as _time

        ts = int(_time.time())
        mock_response = {
            "parsed": [
                {
                    "price": 5000000000,  # price in base units with expo -8 -> 50.00
                    "conf": 0,
                    "expo": -8,
                    "publish_time": ts - 1,  # fresh
                }
            ]
        }

        with patch("aiohttp.ClientSession.get") as mock_get:
            # Set status=200 and JSON payload
            mock_ctx = mock_get.return_value.__aenter__.return_value
            mock_ctx.status = 200
            mock_ctx.json.return_value = mock_response

            pyth = PythOracle()
            result = await pyth.get_price("BTC/USD")

            # Should scale correctly: result.price is 1e8 fixed-point (50.00 * 1e8)
            assert result.price == 5000000000
            # Close session to avoid warnings
            await pyth.close()

    @pytest.mark.asyncio
    async def test_chainlink_staleness_check(self):
        """Test Chainlink staleness validation."""
        # Build a minimal Web3 stub instance
        mock_web3 = Mock()
        mock_web3.to_checksum_address.side_effect = lambda x: x
        mock_web3.eth = Mock()
        # Mock contract call
        mock_contract = Mock()
        mock_contract.functions.latestRoundData.return_value.call.return_value = (
            1,  # round_id
            5000000000,  # answer (50.00 * 1e8)
            1234567890,  # started_at
            1234567890,  # updated_at
            1,  # answered_in_round
        )
        mock_web3.eth.contract.return_value = mock_contract
        # Mock block with recent timestamp
        mock_block = Mock()
        mock_block.timestamp = 1234567890 + 30  # 30 seconds old
        mock_web3.eth.get_block.return_value = mock_block

        chainlink = ChainlinkOracle(mock_web3)
        # Should pass staleness check
        result = await chainlink.get_price("BTC/USD", max_age_s=60)
        assert result.price == 5000000000

    @pytest.mark.asyncio
    async def test_unsupported_symbol_error(self):
        """Test error handling for unsupported symbols."""
        pyth = PythOracle()

        with pytest.raises(ValueError, match="Unsupported symbol"):
            await pyth.get_price("UNKNOWN/USD")

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test timeout handling in oracle providers."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            # Mock timeout
            mock_get.side_effect = asyncio.TimeoutError("Request timeout")

            pyth = PythOracle()

            with pytest.raises(Exception, match="timeout"):
                await pyth.get_price("BTC/USD")
