"""
Integration Tests for Copy Trading
Tests the complete copy trading flow from leader trade to execution
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from src.copy_trading.copy_executor import CopyExecutor
from src.copy_trading.leaderboard_service import LeaderboardService
from src.ai.trader_analyzer import TraderAnalyzer
from src.ai.market_intelligence import MarketIntelligence
from src.analytics.position_tracker import PositionTracker

class TestIntegration:
    @pytest.mark.asyncio
    async def test_full_copy_trading_flow(self):
        """Test complete copy trading flow from leader trade to execution"""
        
        # Setup mocks
        db_pool = AsyncMock()
        redis_client = AsyncMock()
        avantis_client = AsyncMock()
        config = MagicMock()
        
        # Initialize services
        position_tracker = PositionTracker(db_pool, redis_client, config)
        trader_analyzer = TraderAnalyzer(db_pool, redis_client, config)
        market_intelligence = MarketIntelligence(config, db_pool, redis_client)
        leaderboard_service = LeaderboardService(db_pool, redis_client, trader_analyzer, config)
        copy_executor = CopyExecutor(db_pool, redis_client, avantis_client, market_intelligence, config)
        
        # Mock configuration
        config_data = {
            'copytrader_id': 1,
            'user_id': 123,
            'leader_address': '0x1234567890123456789012345678901234567890',
            'is_enabled': True,
            'sizing_mode': 'FIXED_NOTIONAL',
            'sizing_value': 1000,
            'max_slippage_bps': 100,
            'pair_filters': {}
        }
        
        # Mock leader trade
        leader_trade = {
            'address': config_data['leader_address'],
            'pair_symbol': 'BTC-USD',
            'is_long': True,
            'size': 1.0,
            'price': 50000,
            'leverage': 10,
            'event_type': 'OPENED',
            'timestamp': datetime.utcnow(),
            'trade_id': 'trade_123'
        }
        
        # Mock database responses
        conn = AsyncMock()
        db_pool.acquire.return_value.__aenter__.return_value = conn
        conn.fetch.return_value = [config_data]
        conn.fetchrow.return_value = {'id': 1, 'user_id': 123}
        conn.execute.return_value = None
        
        # Mock Avantis client
        avantis_client.execute_trade.return_value = '0xmocktxhash'
        
        # Mock market intelligence
        market_intelligence.get_copy_timing_signal = AsyncMock(return_value=MagicMock(signal='green'))
        
        # Mock Redis operations
        redis_client.get.return_value = None
        redis_client.set.return_value = None
        redis_client.setex.return_value = None
        
        # 1. Simulate leader trade detection
        await copy_executor._get_new_leader_trades(config_data['leader_address'])
        
        # 2. Check if copy should be executed
        should_copy = await copy_executor._should_copy_trade(config_data, leader_trade)
        assert should_copy == True
        
        # 3. Create copy request
        copy_request = await copy_executor._create_copy_request(config_data, leader_trade)
        assert copy_request.target_size == 1000 / 50000  # $1000 / $50000 price
        
        # 4. Execute copy trade
        await copy_executor._execute_copy_trade(copy_request)
        
        # Verify trade was executed
        avantis_client.execute_trade.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_telegram_bot_integration(self):
        """Test Telegram bot handlers with copy trading"""
        
        # Mock bot components
        bot = AsyncMock()
        message = MagicMock()
        message.from_user.id = 123
        message.text = "/alfa top50"
        
        # Mock services
        leaderboard_service = AsyncMock()
        leaderboard_service.get_top_traders.return_value = [
            {
                'address': '0x123',
                'copyability_score': 85,
                'last_30d_volume_usd': 1000000,
                'realized_pnl_clean_usd': 50000,
                'archetype': 'Risk Manager'
            }
        ]
        
        # Test leaderboard command
        from src.bot.handlers.copytrading_handlers import alfa_leaderboard
        await alfa_leaderboard(message)
        
        # Verify service was called
        leaderboard_service.get_top_traders.assert_called_once_with(limit=10)
    
    @pytest.mark.asyncio
    async def test_ai_analysis_integration(self):
        """Test AI analysis integration with copy trading"""
        
        # Setup mocks
        db_pool = AsyncMock()
        redis_client = AsyncMock()
        config = MagicMock()
        
        # Initialize services
        position_tracker = PositionTracker(db_pool, redis_client, config)
        trader_analyzer = TraderAnalyzer(db_pool, redis_client, config)
        
        # Mock trader stats
        stats = MagicMock()
        stats.address = '0x123'
        stats.last_30d_volume_usd = 1000000
        stats.trade_count_30d = 100
        stats.win_rate = 0.65
        stats.maker_ratio = 0.3
        stats.unique_symbols = 5
        stats.median_trade_size_usd = 10000
        stats.realized_pnl_clean_usd = 50000
        stats.last_trade_at = datetime.utcnow()
        stats.avg_hold_time_hours = 2.5
        stats.leverage_consistency = 0.8
        
        # Mock trades
        trades = [
            {
                'event_type': 'CLOSED',
                'pnl': 100,
                'timestamp': datetime.utcnow() - timedelta(days=i)
            }
            for i in range(20)
        ]
        
        # Test AI analysis
        analysis = await trader_analyzer.analyze_trader('0x123', stats, trades)
        
        # Verify analysis
        assert analysis.address == '0x123'
        assert analysis.archetype in ['Unknown', 'Conservative Scalper', 'Risk Manager', 'Precision Trader', 'Volume Hunter', 'Aggressive Swinger']
        assert 0.0 <= analysis.performance_score <= 1.0
        assert analysis.risk_level in ['LOW', 'MED', 'HIGH']
        assert len(analysis.strengths) > 0
        assert len(analysis.warnings) > 0
    
    @pytest.mark.asyncio
    async def test_market_intelligence_integration(self):
        """Test market intelligence integration"""
        
        # Setup mocks
        config = MagicMock()
        db_pool = AsyncMock()
        redis_client = AsyncMock()
        
        # Initialize service
        market_intelligence = MarketIntelligence(config, db_pool, redis_client)
        
        # Mock price data
        market_intelligence.price_feeds = {
            'BTC-USD': {
                'prices': [
                    {'price': 50000, 'timestamp': datetime.utcnow() - timedelta(minutes=i)}
                    for i in range(100)
                ],
                'last_updated': datetime.utcnow()
            }
        }
        
        # Test regime analysis
        regime_metrics = await market_intelligence._calculate_regime_metrics('BTC-USD')
        
        if regime_metrics:
            assert 'volatility' in regime_metrics
            assert 'trend' in regime_metrics
            assert 'regime_color' in regime_metrics
            assert 'confidence' in regime_metrics
        
        # Test copy timing signal
        signal = await market_intelligence.get_copy_timing_signal('BTC-USD')
        
        assert signal.signal in ['green', 'yellow', 'red']
        assert 0.0 <= signal.confidence <= 1.0
        assert signal.trend in ['bullish', 'bearish', 'neutral']
        assert len(signal.reason) > 0
        assert len(signal.recommendation) > 0
    
    @pytest.mark.asyncio
    async def test_database_integration(self):
        """Test database integration for copy trading"""
        
        # Setup mocks
        db_pool = AsyncMock()
        redis_client = AsyncMock()
        config = MagicMock()
        
        # Mock database operations
        conn = AsyncMock()
        db_pool.acquire.return_value.__aenter__.return_value = conn
        
        # Test trader stats insertion
        conn.execute.return_value = None
        
        position_tracker = PositionTracker(db_pool, redis_client, config)
        
        # Mock trader stats
        stats = MagicMock()
        stats.address = '0x123'
        stats.last_30d_volume_usd = 1000000
        stats.median_trade_size_usd = 10000
        stats.trade_count_30d = 100
        stats.realized_pnl_clean_usd = 50000
        stats.last_trade_at = datetime.utcnow()
        stats.maker_ratio = 0.3
        stats.unique_symbols = 5
        stats.win_rate = 0.65
        stats.avg_hold_time_hours = 2.5
        stats.leverage_consistency = 0.8
        
        # Test stats persistence
        await position_tracker._cache_and_persist_stats('0x123', stats)
        
        # Verify database operations
        conn.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_redis_integration(self):
        """Test Redis integration for caching"""
        
        # Setup mocks
        db_pool = AsyncMock()
        redis_client = AsyncMock()
        config = MagicMock()
        
        # Mock Redis operations
        redis_client.setex.return_value = None
        redis_client.get.return_value = None
        
        position_tracker = PositionTracker(db_pool, redis_client, config)
        
        # Test caching
        stats = MagicMock()
        stats.address = '0x123'
        stats.last_30d_volume_usd = 1000000
        stats.median_trade_size_usd = 10000
        stats.trade_count_30d = 100
        stats.realized_pnl_clean_usd = 50000
        stats.last_trade_at = datetime.utcnow()
        stats.maker_ratio = 0.3
        stats.unique_symbols = 5
        stats.win_rate = 0.65
        stats.avg_hold_time_hours = 2.5
        stats.leverage_consistency = 0.8
        
        await position_tracker._cache_and_persist_stats('0x123', stats)
        
        # Verify Redis operations
        redis_client.setex.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self):
        """Test error handling across the system"""
        
        # Setup mocks with errors
        db_pool = AsyncMock()
        redis_client = AsyncMock()
        config = MagicMock()
        
        # Mock database error
        db_pool.acquire.side_effect = Exception("Database connection failed")
        
        # Initialize services
        position_tracker = PositionTracker(db_pool, redis_client, config)
        trader_analyzer = TraderAnalyzer(db_pool, redis_client, config)
        market_intelligence = MarketIntelligence(config, db_pool, redis_client)
        leaderboard_service = LeaderboardService(db_pool, redis_client, trader_analyzer, config)
        
        # Test error handling
        traders = await leaderboard_service.get_top_traders(limit=10)
        assert traders == []
        
        card = await leaderboard_service.get_trader_card('0x123')
        assert card is None
        
        stats = await position_tracker.get_trader_stats('0x123')
        assert stats is None
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test concurrent operations across services"""
        
        # Setup mocks
        db_pool = AsyncMock()
        redis_client = AsyncMock()
        config = MagicMock()
        
        # Mock database operations
        conn = AsyncMock()
        db_pool.acquire.return_value.__aenter__.return_value = conn
        conn.fetch.return_value = []
        conn.fetchrow.return_value = None
        conn.execute.return_value = None
        
        # Mock Redis operations
        redis_client.get.return_value = None
        redis_client.setex.return_value = None
        
        # Initialize services
        position_tracker = PositionTracker(db_pool, redis_client, config)
        trader_analyzer = TraderAnalyzer(db_pool, redis_client, config)
        leaderboard_service = LeaderboardService(db_pool, redis_client, trader_analyzer, config)
        
        # Test concurrent operations
        tasks = [
            leaderboard_service.get_top_traders(limit=10),
            leaderboard_service.get_trader_card('0x123'),
            position_tracker.get_trader_stats('0x123'),
            trader_analyzer.analyze_trader('0x123', MagicMock(), [])
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all operations completed (some may return None/empty due to mocks)
        assert len(results) == 4
        assert all(not isinstance(result, Exception) for result in results)
    
    @pytest.mark.asyncio
    async def test_performance_under_load(self):
        """Test performance under simulated load"""
        
        # Setup mocks
        db_pool = AsyncMock()
        redis_client = AsyncMock()
        config = MagicMock()
        
        # Mock database operations
        conn = AsyncMock()
        db_pool.acquire.return_value.__aenter__.return_value = conn
        conn.fetch.return_value = []
        conn.fetchrow.return_value = None
        conn.execute.return_value = None
        
        # Mock Redis operations
        redis_client.get.return_value = None
        redis_client.setex.return_value = None
        
        # Initialize services
        leaderboard_service = LeaderboardService(db_pool, redis_client, None, config)
        
        # Test performance under load
        start_time = asyncio.get_event_loop().time()
        
        # Simulate 100 concurrent requests
        tasks = [
            leaderboard_service.get_top_traders(limit=10)
            for _ in range(100)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = asyncio.get_event_loop().time()
        elapsed = end_time - start_time
        
        # Should complete 100 requests in under 5 seconds
        assert elapsed < 5.0
        assert len(results) == 100
        assert all(not isinstance(result, Exception) for result in results)
