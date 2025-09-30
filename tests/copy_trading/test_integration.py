"""
Integration tests for copy trading functionality
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ai.market_intelligence import MarketIntelligence
from src.ai.trader_analyzer import TraderAnalyzer
from src.analytics.data_extractor import AvantisEventIndexer
from src.analytics.position_tracker import PositionTracker
from src.copy_trading.copy_executor import CopyExecutor
from src.copy_trading.leaderboard_service import LeaderboardService


@pytest.fixture
def mock_services():
    """Create mock services for integration testing"""
    db_pool = AsyncMock()
    redis_client = AsyncMock()
    config = MagicMock()

    # Mock configuration
    config.LEADER_ACTIVE_HOURS = 72
    config.LEADER_MIN_TRADES_30D = 300
    config.LEADER_MIN_VOLUME_30D_USD = 10000000
    config.BASE_WS_URL = "wss://test.example.com"
    config.AVANTIS_TRADING_CONTRACT = "0x123"
    config.PYTH_PRICE_FEED_IDS_JSON = '{"BTC-USD": "0xabc", "ETH-USD": "0xdef"}'

    # Create services
    event_indexer = AvantisEventIndexer(config, db_pool, redis_client)
    position_tracker = PositionTracker(db_pool, redis_client, config)
    trader_analyzer = TraderAnalyzer(config)
    market_intelligence = MarketIntelligence(config)

    avantis_client = AsyncMock()
    copy_executor = CopyExecutor(
        db_pool, redis_client, avantis_client, market_intelligence, config
    )
    leaderboard_service = LeaderboardService(
        db_pool, redis_client, trader_analyzer, config
    )

    return {
        "db_pool": db_pool,
        "redis_client": redis_client,
        "config": config,
        "event_indexer": event_indexer,
        "position_tracker": position_tracker,
        "trader_analyzer": trader_analyzer,
        "market_intelligence": market_intelligence,
        "copy_executor": copy_executor,
        "leaderboard_service": leaderboard_service,
    }


@pytest.mark.asyncio
async def test_copy_trading_workflow(mock_services):
    """Test complete copy trading workflow"""
    services = mock_services
    copy_executor = services["copy_executor"]
    leaderboard_service = services["leaderboard_service"]

    # Mock database responses
    conn = AsyncMock()
    services["db_pool"].acquire.return_value.__aenter__.return_value = conn

    # Test 1: Create copytrader profile
    conn.fetchrow.return_value = None  # No existing profile
    conn.fetchval.return_value = 1  # New copytrader ID
    conn.execute.return_value = None

    user_id = 123
    leader_address = "0xabc123"
    config = {
        "sizing_mode": "FIXED_NOTIONAL",
        "sizing_value": 100.0,
        "max_slippage_bps": 100,
        "max_leverage": 50.0,
        "notional_cap": 1000.0,
    }

    result = await copy_executor.follow_trader(user_id, leader_address, config)
    assert result["success"] is True

    # Test 2: Get leaderboard
    mock_traders = [
        {
            "address": "0xabc123",
            "last_30d_volume_usd": 1000000,
            "realized_pnl_clean_usd": 50000,
            "trade_count_30d": 500,
            "archetype": "Conservative Scalper",
            "risk_level": "MED",
            "sharpe_like": 1.5,
            "consistency": 0.8,
            "last_trade_at": datetime.utcnow(),
            "maker_ratio": 0.3,
            "unique_symbols": 5,
        }
    ]

    conn.fetch.return_value = mock_traders
    services["redis_client"].get.return_value = None  # No cache

    traders = await leaderboard_service.get_top_traders(limit=10)
    assert len(traders) > 0

    # Test 3: Get copy status
    conn.fetch.side_effect = [
        [],  # profiles
        [],  # follows
        [],  # positions
    ]

    status = await copy_executor.get_copy_status(user_id)
    assert "profiles" in status
    assert "following" in status
    assert "performance" in status


@pytest.mark.asyncio
async def test_trader_analysis_workflow(mock_services):
    """Test trader analysis workflow"""
    services = mock_services
    trader_analyzer = services["trader_analyzer"]
    services["leaderboard_service"]

    # Mock trader data
    from src.analytics.position_tracker import TraderStats

    stats = TraderStats(
        address="0xabc123",
        last_30d_volume_usd=1000000,
        median_trade_size_usd=5000,
        trade_count_30d=500,
        realized_pnl_clean_usd=50000,
        last_trade_at=datetime.utcnow(),
        maker_ratio=0.3,
        unique_symbols=5,
        win_rate=0.6,
    )

    trades = [
        {
            "pair": "0",
            "is_long": True,
            "size": 1.0,
            "price": 50000,
            "leverage": 10,
            "timestamp": datetime.utcnow(),
            "event_type": "OPENED",
        },
        {
            "pair": "0",
            "is_long": True,
            "size": 1.0,
            "price": 51000,
            "leverage": 10,
            "timestamp": datetime.utcnow() + timedelta(hours=1),
            "event_type": "CLOSED",
            "pnl": 1000,
        },
    ]

    # Test trader analysis
    analysis = await trader_analyzer.analyze_trader("0xabc123", stats, trades)

    assert analysis.address == "0xabc123"
    assert analysis.performance_score >= 0.0
    assert analysis.performance_score <= 1.0
    assert analysis.risk_level in ["LOW", "MED", "HIGH"]
    assert len(analysis.strengths) > 0


@pytest.mark.asyncio
async def test_market_intelligence_workflow(mock_services):
    """Test market intelligence workflow"""
    services = mock_services
    market_intelligence = services["market_intelligence"]

    # Mock price data
    with patch.object(market_intelligence, "_fetch_pyth_price") as mock_fetch:
        mock_fetch.return_value = {
            "symbol": "BTC-USD",
            "price": 50000.0,
            "timestamp": datetime.utcnow(),
            "confidence": 0.95,
            "source": "pyth",
        }

        # Test price monitoring
        await market_intelligence._update_regime_analysis(
            "BTC-USD", mock_fetch.return_value
        )

        # Test signal generation
        signal = await market_intelligence.get_copy_timing_signal("BTC-USD")

        assert signal.symbol == "BTC-USD"
        assert signal.signal in ["green", "yellow", "red"]
        assert 0.0 <= signal.confidence <= 1.0


@pytest.mark.asyncio
async def test_event_indexing_workflow(mock_services):
    """Test event indexing workflow"""
    services = mock_services
    event_indexer = services["event_indexer"]

    # Mock Web3 and contract
    with patch.object(event_indexer, "web3") as mock_web3:
        mock_web3.eth.block_number = 1000000
        mock_web3.eth.get_block.return_value = {
            "timestamp": int(datetime.utcnow().timestamp())
        }

        # Mock contract events
        mock_event = MagicMock()
        mock_event.args.trader = "0xabc123"
        mock_event.args.pairIndex = 0
        mock_event.args.long = True
        mock_event.args.positionSizeDai = 1000000000000000000  # 1 DAI
        mock_event.args.openPrice = 5000000000000  # $50,000
        mock_event.args.leverage = 10
        mock_event.blockNumber = 1000000
        mock_event.transactionHash.hex.return_value = "0x123"

        mock_filter = MagicMock()
        mock_filter.get_all_entries.return_value = [mock_event]

        with patch.object(
            event_indexer.trading_contract.events, "TradeOpened"
        ) as mock_events:
            mock_events.create_filter.return_value = mock_filter

            # Mock database persistence
            conn = AsyncMock()
            services["db_pool"].acquire.return_value.__aenter__.return_value = conn

            # Test event processing
            await event_indexer._process_block_range(999999, 1000000)

            # Verify database was called
            conn.executemany.assert_called_once()


@pytest.mark.asyncio
async def test_position_tracking_workflow(mock_services):
    """Test position tracking workflow"""
    services = mock_services
    position_tracker = services["position_tracker"]

    # Mock database responses
    conn = AsyncMock()
    services["db_pool"].acquire.return_value.__aenter__.return_value = conn

    # Mock trader trades
    mock_trades = [
        {
            "pair": "0",
            "is_long": True,
            "size": 1.0,
            "price": 50000,
            "leverage": 10,
            "event_type": "OPENED",
            "timestamp": datetime.utcnow(),
            "fee": 10,
        },
        {
            "pair": "0",
            "is_long": True,
            "size": 1.0,
            "price": 51000,
            "leverage": 10,
            "event_type": "CLOSED",
            "timestamp": datetime.utcnow() + timedelta(hours=1),
            "fee": 10,
            "pnl": 1000,
        },
    ]

    conn.fetch.return_value = mock_trades
    conn.execute.return_value = None

    # Mock Redis
    services["redis_client"].hset.return_value = None
    services["redis_client"].expire.return_value = None

    # Test trader stats calculation
    stats = await position_tracker._calculate_trader_stats(
        "0xabc123", datetime.utcnow() - timedelta(days=30)
    )

    assert stats is not None
    assert stats.address == "0xabc123"
    assert stats.last_30d_volume_usd > 0
    assert stats.trade_count_30d == 2


@pytest.mark.asyncio
async def test_error_handling(mock_services):
    """Test error handling in copy trading workflow"""
    services = mock_services
    copy_executor = services["copy_executor"]

    # Test invalid configuration
    invalid_config = {"sizing_mode": "INVALID_MODE", "sizing_value": 100.0}

    result = await copy_executor.follow_trader(123, "0xabc123", invalid_config)
    assert result["success"] is False
    assert "error" in result

    # Test unfollowing non-existent trader
    conn = AsyncMock()
    services["db_pool"].acquire.return_value.__aenter__.return_value = conn
    conn.execute.return_value = None

    result = await copy_executor.unfollow_trader(123, "0xnonexistent")
    assert result["success"] is True  # Should not fail


@pytest.mark.asyncio
async def test_performance_under_load(mock_services):
    """Test performance under simulated load"""
    services = mock_services
    leaderboard_service = services["leaderboard_service"]

    # Mock large dataset
    conn = AsyncMock()
    services["db_pool"].acquire.return_value.__aenter__.return_value = conn

    # Create mock data for 1000 traders
    mock_traders = []
    for i in range(1000):
        mock_traders.append(
            {
                "address": f"0x{hex(i)[2:].zfill(40)}",
                "last_30d_volume_usd": 1000000 + i * 1000,
                "realized_pnl_clean_usd": 50000 + i * 100,
                "trade_count_30d": 500 + i,
                "archetype": "Conservative Scalper",
                "risk_level": "MED",
                "sharpe_like": 1.5,
                "consistency": 0.8,
                "last_trade_at": datetime.utcnow(),
                "maker_ratio": 0.3,
                "unique_symbols": 5,
            }
        )

    conn.fetch.return_value = mock_traders
    services["redis_client"].get.return_value = None  # No cache

    # Test leaderboard generation performance
    start_time = datetime.utcnow()
    traders = await leaderboard_service.get_top_traders(limit=50)
    end_time = datetime.utcnow()

    processing_time = (end_time - start_time).total_seconds()

    assert len(traders) == 50
    assert processing_time < 5.0  # Should complete within 5 seconds


@pytest.mark.asyncio
async def test_data_consistency(mock_services):
    """Test data consistency across services"""
    services = mock_services
    services["copy_executor"]
    leaderboard_service = services["leaderboard_service"]

    # Mock database responses
    conn = AsyncMock()
    services["db_pool"].acquire.return_value.__aenter__.return_value = conn

    # Create consistent mock data
    trader_address = "0xabc123"
    volume = 1000000
    pnl = 50000

    # Mock trader stats
    conn.fetchrow.return_value = {
        "address": trader_address,
        "last_30d_volume_usd": volume,
        "realized_pnl_clean_usd": pnl,
        "trade_count_30d": 500,
        "unique_symbols": 5,
    }

    # Test leaderboard service
    conn.fetch.return_value = [
        {
            "address": trader_address,
            "last_30d_volume_usd": volume,
            "realized_pnl_clean_usd": pnl,
            "trade_count_30d": 500,
            "archetype": "Conservative Scalper",
            "risk_level": "MED",
            "sharpe_like": 1.5,
            "consistency": 0.8,
            "last_trade_at": datetime.utcnow(),
            "maker_ratio": 0.3,
            "unique_symbols": 5,
        }
    ]

    services["redis_client"].get.return_value = None

    traders = await leaderboard_service.get_top_traders(limit=10)
    assert len(traders) > 0
    assert traders[0]["address"] == trader_address
    assert traders[0]["last_30d_volume_usd"] == volume
    assert traders[0]["realized_pnl_clean_usd"] == pnl


@pytest.mark.asyncio
async def test_concurrent_operations(mock_services):
    """Test concurrent operations"""
    services = mock_services
    copy_executor = services["copy_executor"]

    # Mock database responses
    conn = AsyncMock()
    services["db_pool"].acquire.return_value.__aenter__.return_value = conn

    conn.fetchrow.return_value = None  # No existing profile
    conn.fetchval.return_value = 1  # New copytrader ID
    conn.execute.return_value = None

    # Create multiple concurrent follow requests
    async def follow_trader(user_id, leader_address):
        config = {
            "sizing_mode": "FIXED_NOTIONAL",
            "sizing_value": 100.0,
            "max_slippage_bps": 100,
            "max_leverage": 50.0,
            "notional_cap": 1000.0,
        }
        return await copy_executor.follow_trader(user_id, leader_address, config)

    # Run concurrent operations
    tasks = []
    for i in range(10):
        task = asyncio.create_task(follow_trader(i, f"0x{hex(i)[2:].zfill(40)}"))
        tasks.append(task)

    results = await asyncio.gather(*tasks)

    # All should succeed
    for result in results:
        assert result["success"] is True


if __name__ == "__main__":
    pytest.main([__file__])
