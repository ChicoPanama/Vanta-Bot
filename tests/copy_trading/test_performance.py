"""
Performance Tests for Copy Trading
Tests performance under load and optimization
"""

import os
import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from src.copy_trading.leaderboard_service import LeaderboardService
from src.copy_trading.copy_executor import CopyExecutor
from src.ai.trader_analyzer import TraderAnalyzer
from src.analytics.position_tracker import PositionTracker

pytestmark = pytest.mark.skipif(not os.getenv("RUN_SLOW"), reason="slow suite; set RUN_SLOW=1 to enable")

class TestPerformance:
    @pytest.mark.asyncio
    async def test_leaderboard_response_time(self):
        """Test leaderboard generation performance"""
        start_time = time.time()
        
        # Mock database with 1000 traders
        db_pool = AsyncMock()
        conn = AsyncMock()
        db_pool.acquire.return_value.__aenter__.return_value = conn
        
        # Generate mock trader data
        traders = [
            {
                'address': f'0x{i:040x}',
                'last_30d_volume_usd': 1000000 - i * 1000,
                'realized_pnl_clean_usd': 50000 - i * 100,
                'trade_count_30d': 500 - i,
                'last_trade_at': datetime.utcnow() - timedelta(hours=i % 24),
                'maker_ratio': 0.3,
                'unique_symbols': 5,
                'win_rate': 0.65,
                'archetype': 'Risk Manager',
                'risk_level': 'MED',
                'sharpe_like': 1.2,
                'consistency': 0.8
            }
            for i in range(1000)
        ]
        
        conn.fetch.return_value = traders
        
        # Mock Redis
        redis_client = AsyncMock()
        redis_client.get.return_value = None  # No cache
        redis_client.setex.return_value = None
        
        # Mock AI analyzer
        trader_analyzer = AsyncMock()
        trader_analyzer._get_ai_analysis.return_value = {
            'archetype': 'Risk Manager',
            'risk_level': 'MED',
            'sharpe_like': 1.2,
            'consistency': 0.8
        }
        
        config = MagicMock()
        service = LeaderboardService(db_pool, redis_client, trader_analyzer, config)
        
        top_traders = await service.get_top_traders(limit=50)
        
        elapsed = time.time() - start_time
        
        assert len(top_traders) == 50
        assert elapsed < 2.0  # Should complete in under 2 seconds
    
    @pytest.mark.asyncio
    async def test_concurrent_copy_execution(self):
        """Test handling multiple copy requests simultaneously"""
        # Setup mocks
        db_pool = AsyncMock()
        redis_client = AsyncMock()
        avantis_client = AsyncMock()
        market_intelligence = AsyncMock()
        config = MagicMock()
        
        executor = CopyExecutor(db_pool, redis_client, avantis_client, market_intelligence, config)
        
        # Mock successful execution
        executor._get_current_price = AsyncMock(return_value=50000)
        executor._execute_avantis_trade = AsyncMock(return_value='0xmocktxhash')
        executor._get_user_id = AsyncMock(return_value=123)
        executor._get_max_leverage = AsyncMock(return_value=50)
        executor._record_copy_position = AsyncMock()
        executor._send_copy_notification = AsyncMock()
        
        # Create 10 concurrent copy requests
        from src.copy_trading.copy_executor import CopyTradeRequest
        requests = [
            CopyTradeRequest(
                copytrader_id=i,
                leader_address=f'0x{i:040x}',
                trade_data={'pair_symbol': 'BTC-USD', 'price': 50000, 'is_long': True, 'leverage': 10},
                original_size=1.0,
                target_size=0.1,
                max_slippage_bps=100
            )
            for i in range(10)
        ]
        
        start_time = time.time()
        
        # Execute all requests concurrently
        tasks = [executor._execute_copy_trade(req) for req in requests]
        await asyncio.gather(*tasks)
        
        elapsed = time.time() - start_time
        
        # Should handle 10 concurrent executions in under 5 seconds
        assert elapsed < 5.0
        assert executor._execute_avantis_trade.call_count == 10
    
    def test_fifo_calculation_large_dataset(self):
        """Test FIFO calculation with large number of trades"""
        # Generate 10,000 trades
        trades = []
        for i in range(10000):
            if i % 3 == 0:  # Every 3rd trade is an open
                trades.append({
                    'event_type': 'OPENED',
                    'pair_symbol': 'BTC-USD',
                    'size': 0.1,
                    'price': 50000 + (i % 100) * 100,
                    'is_long': True,
                    'timestamp': datetime(2024, 1, 1) + timedelta(minutes=i),
                    'fee': 1
                })
            else:  # Close trades
                trades.append({
                    'event_type': 'CLOSED',
                    'pair_symbol': 'BTC-USD',
                    'size': 0.1,
                    'price': 50000 + (i % 100) * 100 + 500,
                    'is_long': True,
                    'timestamp': datetime(2024, 1, 1) + timedelta(minutes=i),
                    'fee': 1
                })
        
        tracker = PositionTracker(None, None, None)
        
        start_time = time.time()
        pnl = tracker._calculate_fifo_pnl(trades)
        elapsed = time.time() - start_time
        
        # Should process 10k trades in under 1 second
        assert elapsed < 1.0
        assert isinstance(pnl, float)
    
    @pytest.mark.asyncio
    async def test_ai_analysis_performance(self):
        """Test AI analysis performance"""
        # Setup mocks
        db_pool = AsyncMock()
        redis_client = AsyncMock()
        config = MagicMock()
        
        analyzer = TraderAnalyzer(db_pool, redis_client, config)
        
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
            for i in range(100)
        ]
        
        start_time = time.time()
        
        # Test analysis
        analysis = await analyzer.analyze_trader('0x123', stats, trades)
        
        elapsed = time.time() - start_time
        
        # Should complete analysis in under 1 second
        assert elapsed < 1.0
        assert analysis.address == '0x123'
        assert analysis.archetype is not None
        assert 0.0 <= analysis.performance_score <= 1.0
    
    @pytest.mark.asyncio
    async def test_market_intelligence_performance(self):
        """Test market intelligence performance"""
        # Setup mocks
        config = MagicMock()
        db_pool = AsyncMock()
        redis_client = AsyncMock()
        
        from src.ai.market_intelligence import MarketIntelligence
        market_intel = MarketIntelligence(config, db_pool, redis_client)
        
        # Mock price data
        market_intel.price_feeds = {
            'BTC-USD': {
                'prices': [
                    {'price': 50000 + i * 100, 'timestamp': datetime.utcnow() - timedelta(minutes=i)}
                    for i in range(1000)
                ],
                'last_updated': datetime.utcnow()
            }
        }
        
        start_time = time.time()
        
        # Test regime analysis
        regime_metrics = await market_intel._calculate_regime_metrics('BTC-USD')
        
        elapsed = time.time() - start_time
        
        # Should complete analysis in under 0.5 seconds
        assert elapsed < 0.5
        if regime_metrics:
            assert 'volatility' in regime_metrics
            assert 'trend' in regime_metrics
            assert 'regime_color' in regime_metrics
    
    @pytest.mark.asyncio
    async def test_database_query_performance(self):
        """Test database query performance"""
        # Setup mocks
        db_pool = AsyncMock()
        redis_client = AsyncMock()
        config = MagicMock()
        
        # Mock database operations
        conn = AsyncMock()
        db_pool.acquire.return_value.__aenter__.return_value = conn
        
        # Mock query results
        conn.fetch.return_value = [
            {
                'address': f'0x{i:040x}',
                'last_30d_volume_usd': 1000000 - i * 1000,
                'realized_pnl_clean_usd': 50000 - i * 100,
                'trade_count_30d': 500 - i,
                'last_trade_at': datetime.utcnow() - timedelta(hours=i % 24),
                'maker_ratio': 0.3,
                'unique_symbols': 5,
                'win_rate': 0.65,
                'archetype': 'Risk Manager',
                'risk_level': 'MED',
                'sharpe_like': 1.2,
                'consistency': 0.8
            }
            for i in range(1000)
        ]
        
        # Mock Redis
        redis_client.get.return_value = None
        redis_client.setex.return_value = None
        
        # Mock AI analyzer
        trader_analyzer = AsyncMock()
        trader_analyzer._get_ai_analysis.return_value = {
            'archetype': 'Risk Manager',
            'risk_level': 'MED',
            'sharpe_like': 1.2,
            'consistency': 0.8
        }
        
        service = LeaderboardService(db_pool, redis_client, trader_analyzer, config)
        
        start_time = time.time()
        
        # Test multiple queries
        tasks = [
            service.get_top_traders(limit=50),
            service.get_trader_card('0x123'),
            service.get_leaderboard_stats(),
            service.search_traders('0x123', limit=20)
        ]
        
        results = await asyncio.gather(*tasks)
        
        elapsed = time.time() - start_time
        
        # Should complete all queries in under 3 seconds
        assert elapsed < 3.0
        assert len(results) == 4
    
    @pytest.mark.asyncio
    async def test_redis_cache_performance(self):
        """Test Redis cache performance"""
        # Setup mocks
        db_pool = AsyncMock()
        redis_client = AsyncMock()
        config = MagicMock()
        
        # Mock Redis operations
        redis_client.get.return_value = None  # Cache miss
        redis_client.setex.return_value = None
        
        # Mock database operations
        conn = AsyncMock()
        db_pool.acquire.return_value.__aenter__.return_value = conn
        conn.fetch.return_value = []
        
        # Mock AI analyzer
        trader_analyzer = AsyncMock()
        trader_analyzer._get_ai_analysis.return_value = None
        
        service = LeaderboardService(db_pool, redis_client, trader_analyzer, config)
        
        start_time = time.time()
        
        # Test cache operations
        for i in range(100):
            await service.get_top_traders(limit=10)
        
        elapsed = time.time() - start_time
        
        # Should complete 100 cache operations in under 2 seconds
        assert elapsed < 2.0
        assert redis_client.get.call_count == 100
        assert redis_client.setex.call_count == 100
    
    @pytest.mark.asyncio
    async def test_memory_usage_optimization(self):
        """Test memory usage optimization"""
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Setup mocks
        db_pool = AsyncMock()
        redis_client = AsyncMock()
        config = MagicMock()
        
        # Mock database operations
        conn = AsyncMock()
        db_pool.acquire.return_value.__aenter__.return_value = conn
        conn.fetch.return_value = []
        
        # Mock Redis
        redis_client.get.return_value = None
        redis_client.setex.return_value = None
        
        # Mock AI analyzer
        trader_analyzer = AsyncMock()
        trader_analyzer._get_ai_analysis.return_value = None
        
        service = LeaderboardService(db_pool, redis_client, trader_analyzer, config)
        
        # Perform operations
        for i in range(1000):
            await service.get_top_traders(limit=10)
        
        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB)
        assert memory_increase < 100
    
    @pytest.mark.asyncio
    async def test_error_recovery_performance(self):
        """Test error recovery performance"""
        # Setup mocks with intermittent errors
        db_pool = AsyncMock()
        redis_client = AsyncMock()
        config = MagicMock()
        
        # Mock database with intermittent failures
        conn = AsyncMock()
        db_pool.acquire.return_value.__aenter__.return_value = conn
        
        # Simulate 10% failure rate
        import random
        def mock_fetch(*args, **kwargs):
            if random.random() < 0.1:  # 10% failure rate
                raise Exception("Database error")
            return []
        
        conn.fetch.side_effect = mock_fetch
        
        # Mock Redis
        redis_client.get.return_value = None
        redis_client.setex.return_value = None
        
        # Mock AI analyzer
        trader_analyzer = AsyncMock()
        trader_analyzer._get_ai_analysis.return_value = None
        
        service = LeaderboardService(db_pool, redis_client, trader_analyzer, config)
        
        start_time = time.time()
        
        # Test error recovery
        tasks = [
            service.get_top_traders(limit=10)
            for _ in range(100)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        elapsed = time.time() - start_time
        
        # Should complete in reasonable time despite errors
        assert elapsed < 10.0
        assert len(results) == 100
        
        # Some results should be empty lists (successful recovery)
        # Some results should be exceptions (failed operations)
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        error_count = sum(1 for r in results if isinstance(r, Exception))
        
        assert success_count > 0
        assert error_count > 0
        assert success_count + error_count == 100
    
    @pytest.mark.asyncio
    async def test_scalability_limits(self):
        """Test scalability limits"""
        # Setup mocks
        db_pool = AsyncMock()
        redis_client = AsyncMock()
        config = MagicMock()
        
        # Mock database operations
        conn = AsyncMock()
        db_pool.acquire.return_value.__aenter__.return_value = conn
        conn.fetch.return_value = []
        
        # Mock Redis
        redis_client.get.return_value = None
        redis_client.setex.return_value = None
        
        # Mock AI analyzer
        trader_analyzer = AsyncMock()
        trader_analyzer._get_ai_analysis.return_value = None
        
        service = LeaderboardService(db_pool, redis_client, trader_analyzer, config)
        
        # Test with increasing load
        for concurrent_requests in [10, 50, 100, 200]:
            start_time = time.time()
            
            tasks = [
                service.get_top_traders(limit=10)
                for _ in range(concurrent_requests)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            elapsed = time.time() - start_time
            
            # Should scale reasonably
            assert elapsed < concurrent_requests * 0.1  # Less than 0.1s per request
            assert len(results) == concurrent_requests
            assert all(not isinstance(r, Exception) for r in results)
    
    @pytest.mark.asyncio
    async def test_throughput_benchmark(self):
        """Test throughput benchmark"""
        # Setup mocks
        db_pool = AsyncMock()
        redis_client = AsyncMock()
        config = MagicMock()
        
        # Mock database operations
        conn = AsyncMock()
        db_pool.acquire.return_value.__aenter__.return_value = conn
        conn.fetch.return_value = []
        
        # Mock Redis
        redis_client.get.return_value = None
        redis_client.setex.return_value = None
        
        # Mock AI analyzer
        trader_analyzer = AsyncMock()
        trader_analyzer._get_ai_analysis.return_value = None
        
        service = LeaderboardService(db_pool, redis_client, trader_analyzer, config)
        
        # Benchmark throughput
        start_time = time.time()
        
        # Simulate 1 minute of operations
        operations = 0
        while time.time() - start_time < 1.0:  # 1 second benchmark
            await service.get_top_traders(limit=10)
            operations += 1
        
        elapsed = time.time() - start_time
        throughput = operations / elapsed
        
        # Should achieve at least 100 operations per second
        assert throughput >= 100
        print(f"Throughput: {throughput:.2f} operations/second")
