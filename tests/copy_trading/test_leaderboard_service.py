"""
Test Leaderboard Service
Tests the leaderboard service and trader rankings
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from src.copy_trading.leaderboard_service import LeaderboardService

class TestLeaderboardService:
    @pytest.mark.asyncio
    async def test_get_top_traders(self):
        """Test getting top traders"""
        service = LeaderboardService(None, None, None, None)
        
        # Mock database operations
        service.db_pool = AsyncMock()
        conn = AsyncMock()
        service.db_pool.acquire.return_value.__aenter__.return_value = conn
        
        # Mock query results
        conn.fetch.return_value = [
            {
                'address': '0x123',
                'last_30d_volume_usd': 1000000,
                'realized_pnl_clean_usd': 50000,
                'trade_count_30d': 100,
                'last_trade_at': datetime.utcnow(),
                'maker_ratio': 0.3,
                'unique_symbols': 5,
                'win_rate': 0.65,
                'archetype': 'Risk Manager',
                'risk_level': 'MED',
                'sharpe_like': 1.2,
                'consistency': 0.8
            }
        ]
        
        # Mock Redis cache
        service.redis = AsyncMock()
        service.redis.get.return_value = None  # No cache
        service.redis.setex.return_value = None
        
        # Mock AI analysis
        service._get_ai_analysis = AsyncMock(return_value={
            'archetype': 'Risk Manager',
            'risk_level': 'MED',
            'sharpe_like': 1.2,
            'consistency': 0.8
        })
        
        traders = await service.get_top_traders(limit=10)
        
        assert len(traders) == 1
        assert traders[0]['address'] == '0x123'
        assert 'ranking_score' in traders[0]
        assert 'copyability_score' in traders[0]
    
    @pytest.mark.asyncio
    async def test_ranking_algorithm(self):
        """Test trader ranking algorithm"""
        traders = [
            {
                'address': '0x1',
                'last_30d_volume_usd': 1000000,
                'realized_pnl_clean_usd': 50000,
                'consistency': 0.8,
                'last_trade_at': datetime.utcnow() - timedelta(hours=1)
            },
            {
                'address': '0x2',
                'last_30d_volume_usd': 500000,
                'realized_pnl_clean_usd': 100000,
                'consistency': 0.9,
                'last_trade_at': datetime.utcnow() - timedelta(hours=12)
            }
        ]
        
        service = LeaderboardService(None, None, None, None)
        ranked = await service._rank_traders(traders)
        
        # Verify ranking scores are calculated
        assert all('ranking_score' in trader for trader in ranked)
        
        # Higher scores should be first
        assert ranked[0]['ranking_score'] >= ranked[1]['ranking_score']
    
    def test_copyability_score_calculation(self):
        """Test copyability score calculation"""
        trader = {
            'last_30d_volume_usd': 1000000,
            'consistency': 0.8,
            'risk_level': 'MED',
            'win_rate': 0.65,
            'archetype': 'Risk Manager'
        }
        
        service = LeaderboardService(None, None, None, None)
        score = service._calculate_copyability_score(trader)
        
        assert 0 <= score <= 100
        assert isinstance(score, int)
    
    def test_recency_score_calculation(self):
        """Test recency score calculation"""
        service = LeaderboardService(None, None, None, None)
        
        # Recent trade
        recent_time = datetime.utcnow() - timedelta(hours=1)
        score = service._calculate_recency_score(recent_time)
        assert score == 1.0
        
        # Old trade
        old_time = datetime.utcnow() - timedelta(days=30)
        score = service._calculate_recency_score(old_time)
        assert score == 0.2
        
        # No trade
        score = service._calculate_recency_score(None)
        assert score == 0.0
    
    @pytest.mark.asyncio
    async def test_get_trader_card(self):
        """Test getting trader card"""
        service = LeaderboardService(None, None, None, None)
        
        # Mock database operations
        service.db_pool = AsyncMock()
        conn = AsyncMock()
        service.db_pool.acquire.return_value.__aenter__.return_value = conn
        
        # Mock trader stats
        conn.fetchrow.return_value = {
            'address': '0x123',
            'last_30d_volume_usd': 1000000,
            'median_trade_size_usd': 10000,
            'trade_count_30d': 100,
            'realized_pnl_clean_usd': 50000,
            'last_trade_at': datetime.utcnow(),
            'maker_ratio': 0.3,
            'unique_symbols': 5,
            'win_rate': 0.65
        }
        
        # Mock AI analysis
        service._get_ai_analysis = AsyncMock(return_value={
            'archetype': 'Risk Manager',
            'risk_level': 'MED',
            'sharpe_like': 1.2,
            'consistency': 0.8
        })
        
        # Mock recent trades
        service._get_recent_trades = AsyncMock(return_value=[
            {
                'pair_symbol': 'BTC-USD',
                'is_long': True,
                'size': 1.0,
                'price': 50000,
                'leverage': 10,
                'event_type': 'OPENED',
                'timestamp': datetime.utcnow(),
                'tx_hash': '0xabc'
            }
        ])
        
        card = await service.get_trader_card('0x123')
        
        assert card is not None
        assert card['address'] == '0x123'
        assert 'copyability_score' in card
        assert 'strengths' in card
        assert 'warnings' in card
        assert 'optimal_copy_size' in card
    
    @pytest.mark.asyncio
    async def test_get_trader_rankings(self):
        """Test getting trader rankings"""
        service = LeaderboardService(None, None, None, None)
        
        # Mock database operations
        service.db_pool = AsyncMock()
        conn = AsyncMock()
        service.db_pool.acquire.return_value.__aenter__.return_value = conn
        
        # Mock query results
        conn.fetch.return_value = [
            {
                'address': '0x123',
                'last_30d_volume_usd': 1000000,
                'realized_pnl_clean_usd': 50000,
                'trade_count_30d': 100,
                'last_trade_at': datetime.utcnow(),
                'maker_ratio': 0.3,
                'unique_symbols': 5,
                'win_rate': 0.65
            },
            {
                'address': '0x456',
                'last_30d_volume_usd': 500000,
                'realized_pnl_clean_usd': 100000,
                'trade_count_30d': 50,
                'last_trade_at': datetime.utcnow() - timedelta(hours=1),
                'maker_ratio': 0.5,
                'unique_symbols': 3,
                'win_rate': 0.7
            }
        ]
        
        rankings = await service.get_trader_rankings('0x123')
        
        assert rankings is not None
        assert 'overall_rank' in rankings
        assert 'total_traders' in rankings
        assert 'ranking_score' in rankings
        assert 'percentile' in rankings
    
    @pytest.mark.asyncio
    async def test_get_leaderboard_stats(self):
        """Test getting leaderboard statistics"""
        service = LeaderboardService(None, None, None, None)
        
        # Mock database operations
        service.db_pool = AsyncMock()
        conn = AsyncMock()
        service.db_pool.acquire.return_value.__aenter__.return_value = conn
        
        # Mock query results
        conn.fetch.return_value = [
            {
                'address': '0x123',
                'last_30d_volume_usd': 1000000,
                'realized_pnl_clean_usd': 50000,
                'trade_count_30d': 100,
                'win_rate': 0.65,
                'consistency': 0.8,
                'archetype': 'Risk Manager'
            },
            {
                'address': '0x456',
                'last_30d_volume_usd': 500000,
                'realized_pnl_clean_usd': 100000,
                'trade_count_30d': 50,
                'win_rate': 0.7,
                'consistency': 0.9,
                'archetype': 'Conservative Scalper'
            }
        ]
        
        stats = await service.get_leaderboard_stats()
        
        assert 'total_traders' in stats
        assert 'total_volume' in stats
        assert 'total_pnl' in stats
        assert 'avg_win_rate' in stats
        assert 'top_archetype' in stats
        assert stats['total_traders'] == 2
        assert stats['total_volume'] == 1500000
        assert stats['total_pnl'] == 150000
    
    @pytest.mark.asyncio
    async def test_search_traders(self):
        """Test searching traders"""
        service = LeaderboardService(None, None, None, None)
        
        # Mock database operations
        service.db_pool = AsyncMock()
        conn = AsyncMock()
        service.db_pool.acquire.return_value.__aenter__.return_value = conn
        
        # Mock query results
        conn.fetch.return_value = [
            {
                'address': '0x1234567890123456789012345678901234567890',
                'last_30d_volume_usd': 1000000,
                'realized_pnl_clean_usd': 50000,
                'trade_count_30d': 100,
                'last_trade_at': datetime.utcnow(),
                'maker_ratio': 0.3,
                'unique_symbols': 5,
                'win_rate': 0.65,
                'archetype': 'Risk Manager',
                'risk_level': 'MED'
            }
        ]
        
        traders = await service.search_traders('0x123', limit=10)
        
        assert len(traders) == 1
        assert traders[0]['address'].startswith('0x123')
    
    @pytest.mark.asyncio
    async def test_get_trending_traders(self):
        """Test getting trending traders"""
        service = LeaderboardService(None, None, None, None)
        
        # Mock database operations
        service.db_pool = AsyncMock()
        conn = AsyncMock()
        service.db_pool.acquire.return_value.__aenter__.return_value = conn
        
        # Mock query results
        conn.fetch.return_value = [
            {
                'address': '0x123',
                'last_30d_volume_usd': 1000000,
                'realized_pnl_clean_usd': 50000,
                'trade_count_30d': 100,
                'last_trade_at': datetime.utcnow(),
                'maker_ratio': 0.3,
                'unique_symbols': 5,
                'win_rate': 0.65,
                'archetype': 'Risk Manager',
                'risk_level': 'MED',
                'recent_trades': 5
            }
        ]
        
        traders = await service.get_trending_traders(hours=24, limit=5)
        
        assert len(traders) == 1
        assert traders[0]['address'] == '0x123'
        assert traders[0]['recent_trades'] == 5
    
    @pytest.mark.asyncio
    async def test_get_top_performers_by_archetype(self):
        """Test getting top performers by archetype"""
        service = LeaderboardService(None, None, None, None)
        
        # Mock database operations
        service.db_pool = AsyncMock()
        conn = AsyncMock()
        service.db_pool.acquire.return_value.__aenter__.return_value = conn
        
        # Mock query results
        conn.fetch.return_value = [
            {
                'address': '0x123',
                'last_30d_volume_usd': 1000000,
                'realized_pnl_clean_usd': 50000,
                'trade_count_30d': 100,
                'last_trade_at': datetime.utcnow(),
                'maker_ratio': 0.3,
                'unique_symbols': 5,
                'win_rate': 0.65,
                'archetype': 'Risk Manager',
                'risk_level': 'MED',
                'rank': 1
            },
            {
                'address': '0x456',
                'last_30d_volume_usd': 500000,
                'realized_pnl_clean_usd': 100000,
                'trade_count_30d': 50,
                'last_trade_at': datetime.utcnow(),
                'maker_ratio': 0.5,
                'unique_symbols': 3,
                'win_rate': 0.7,
                'archetype': 'Conservative Scalper',
                'risk_level': 'LOW',
                'rank': 1
            }
        ]
        
        performers = await service.get_top_performers_by_archetype(limit=5)
        
        assert 'Risk Manager' in performers
        assert 'Conservative Scalper' in performers
        assert len(performers['Risk Manager']) == 1
        assert len(performers['Conservative Scalper']) == 1
    
    @pytest.mark.asyncio
    async def test_cache_operations(self):
        """Test cache operations"""
        service = LeaderboardService(None, None, None, None)
        
        # Mock Redis operations
        service.redis = AsyncMock()
        service.redis.get.return_value = None  # No cache
        service.redis.setex.return_value = None
        
        # Mock database operations
        service.db_pool = AsyncMock()
        conn = AsyncMock()
        service.db_pool.acquire.return_value.__aenter__.return_value = conn
        
        # Mock query results
        conn.fetch.return_value = []
        
        # Test cache miss
        traders = await service.get_top_traders(limit=10)
        
        # Verify cache operations
        service.redis.get.assert_called_once()
        service.redis.setex.assert_called_once()
        
        # Test cache hit
        service.redis.get.return_value = '{"test": "data"}'
        service.redis.get.side_effect = ['{"test": "data"}', None]  # First call returns cache, second returns None
        
        traders = await service.get_top_traders(limit=10)
        
        # Should not call database on cache hit
        assert conn.fetch.call_count == 1  # Only called once for the first test
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling"""
        service = LeaderboardService(None, None, None, None)
        
        # Mock database error
        service.db_pool = AsyncMock()
        service.db_pool.acquire.side_effect = Exception("Database error")
        
        # Test that errors are handled gracefully
        traders = await service.get_top_traders(limit=10)
        assert traders == []
        
        card = await service.get_trader_card('0x123')
        assert card is None
        
        rankings = await service.get_trader_rankings('0x123')
        assert rankings is None
        
        stats = await service.get_leaderboard_stats()
        assert stats['total_traders'] == 0
