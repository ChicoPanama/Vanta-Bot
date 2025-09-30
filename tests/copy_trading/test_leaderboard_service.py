"""
Tests for Leaderboard Service functionality
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.copy_trading.leaderboard_service import LeaderboardService


@pytest.fixture
def mock_db_pool():
    """Mock database pool"""
    pool = AsyncMock()
    conn = AsyncMock()
    pool.acquire.return_value.__aenter__.return_value = conn
    return pool, conn


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    return AsyncMock()


@pytest.fixture
def mock_trader_analyzer():
    """Mock trader analyzer"""
    return AsyncMock()


@pytest.fixture
def mock_config():
    """Mock configuration"""
    config = MagicMock()
    config.LEADER_ACTIVE_HOURS = 72
    config.LEADER_MIN_TRADES_30D = 300
    config.LEADER_MIN_VOLUME_30D_USD = 10000000
    return config


@pytest.fixture
def leaderboard_service(mock_db_pool, mock_redis, mock_trader_analyzer, mock_config):
    """Create LeaderboardService instance with mocks"""
    db_pool, _ = mock_db_pool
    return LeaderboardService(
        db_pool=db_pool,
        redis_client=mock_redis,
        trader_analyzer=mock_trader_analyzer,
        config=mock_config,
    )


@pytest.mark.asyncio
async def test_leaderboard_service_initialization(leaderboard_service):
    """Test LeaderboardService initialization"""
    assert leaderboard_service is not None
    assert leaderboard_service.cache_ttl == 300


@pytest.mark.asyncio
async def test_get_top_traders_cached(leaderboard_service, mock_redis):
    """Test getting top traders from cache"""
    # Mock cached data

    mock_redis.get.return_value = (
        '{"address": "0xabc123", "last_30d_volume_usd": 1000000}'
    )

    traders = await leaderboard_service.get_top_traders(limit=10)

    # Should return cached data
    mock_redis.get.assert_called_once()
    assert isinstance(traders, list)


@pytest.mark.asyncio
async def test_get_top_traders_no_cache(leaderboard_service, mock_db_pool, mock_redis):
    """Test getting top traders from database when no cache"""
    db_pool, conn = mock_db_pool

    # Mock no cache
    mock_redis.get.return_value = None

    # Mock database response
    mock_rows = [
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

    conn.fetch.return_value = mock_rows
    mock_redis.setex.return_value = None

    await leaderboard_service.get_top_traders(limit=10)

    # Should fetch from database and cache result
    conn.fetch.assert_called_once()
    mock_redis.setex.assert_called_once()


@pytest.mark.asyncio
async def test_calculate_volume_score(leaderboard_service):
    """Test volume score calculation"""
    # Test various volume levels
    assert leaderboard_service._calculate_volume_score(0) == 0.0
    assert leaderboard_service._calculate_volume_score(1000) > 0.0
    assert leaderboard_service._calculate_volume_score(
        1000000
    ) > leaderboard_service._calculate_volume_score(100000)
    assert leaderboard_service._calculate_volume_score(10000000) <= 1.0


@pytest.mark.asyncio
async def test_calculate_pnl_score(leaderboard_service):
    """Test PnL score calculation"""
    # Test positive ROI
    assert leaderboard_service._calculate_pnl_score(50000, 1000000) > 0.5  # 5% ROI
    assert leaderboard_service._calculate_pnl_score(100000, 1000000) > 0.5  # 10% ROI

    # Test negative ROI
    assert leaderboard_service._calculate_pnl_score(-50000, 1000000) < 0.5  # -5% ROI

    # Test zero volume
    assert leaderboard_service._calculate_pnl_score(1000, 0) == 0.5


@pytest.mark.asyncio
async def test_calculate_consistency_score_with_ai_data(leaderboard_service):
    """Test consistency score calculation with AI data"""
    trader = {"consistency": 0.8, "trade_count_30d": 500, "unique_symbols": 5}

    score = leaderboard_service._calculate_consistency_score(trader)

    assert score == 0.8  # Should use AI consistency directly


@pytest.mark.asyncio
async def test_calculate_consistency_score_fallback(leaderboard_service):
    """Test consistency score calculation fallback"""
    trader = {"trade_count_30d": 500, "unique_symbols": 5}

    score = leaderboard_service._calculate_consistency_score(trader)

    assert 0.0 <= score <= 1.0


@pytest.mark.asyncio
async def test_calculate_recency_score(leaderboard_service):
    """Test recency score calculation"""
    now = datetime.utcnow()

    # Recent trade (1 hour ago)
    recent = now - timedelta(hours=1)
    assert leaderboard_service._calculate_recency_score(recent) == 1.0

    # Older trade (1 day ago)
    day_old = now - timedelta(days=1)
    assert leaderboard_service._calculate_recency_score(day_old) == 0.8

    # Very old trade (1 week ago)
    week_old = now - timedelta(weeks=1)
    assert leaderboard_service._calculate_recency_score(week_old) == 0.2

    # No trade
    assert leaderboard_service._calculate_recency_score(None) == 0.0


@pytest.mark.asyncio
async def test_calculate_copyability_score(leaderboard_service):
    """Test copyability score calculation"""
    trader = {
        "last_30d_volume_usd": 1000000,
        "consistency_score": 0.8,
        "risk_level": "MED",
        "pnl_score": 0.7,
        "archetype": "Conservative Scalper",
        "recency_score": 0.9,
    }

    score = leaderboard_service._calculate_copyability_score(trader)

    assert 0 <= score <= 100
    assert score > 50  # Should be above average for good trader


@pytest.mark.asyncio
async def test_get_trader_card_success(leaderboard_service, mock_db_pool, mock_redis):
    """Test getting trader card successfully"""
    db_pool, conn = mock_db_pool

    address = "0xabc123"

    # Mock trader stats
    mock_stats = {
        "address": address,
        "last_30d_volume_usd": 1000000,
        "realized_pnl_clean_usd": 50000,
        "trade_count_30d": 500,
        "unique_symbols": 5,
    }

    conn.fetchrow.return_value = mock_stats
    conn.fetch.return_value = []  # No recent trades
    mock_redis.get.return_value = None  # No cached AI analysis

    card = await leaderboard_service.get_trader_card(address)

    assert card is not None
    assert card["address"] == address
    assert "copyability_score" in card
    assert "strengths" in card
    assert "warnings" in card


@pytest.mark.asyncio
async def test_get_trader_card_not_found(leaderboard_service, mock_db_pool):
    """Test getting trader card when trader not found"""
    db_pool, conn = mock_db_pool

    address = "0xnonexistent"
    conn.fetchrow.return_value = None

    card = await leaderboard_service.get_trader_card(address)

    assert card is None


@pytest.mark.asyncio
async def test_identify_strengths(leaderboard_service):
    """Test identifying trader strengths"""
    stats = {
        "last_30d_volume_usd": 2000000,  # High volume
        "realized_pnl_clean_usd": 100000,  # Positive PnL
        "trade_count_30d": 800,  # High activity
        "unique_symbols": 8,  # Good diversification
    }

    ai_analysis = {"archetype": "Conservative Scalper", "consistency": 0.9}

    strengths = leaderboard_service._identify_strengths(stats, ai_analysis)

    assert len(strengths) <= 3
    assert any("volume" in strength.lower() for strength in strengths)
    assert any("PnL" in strength for strength in strengths)


@pytest.mark.asyncio
async def test_identify_warnings(leaderboard_service):
    """Test identifying trader warnings"""
    stats = {
        "realized_pnl_clean_usd": -20000,  # Losses
        "last_30d_volume_usd": 50000,  # Low volume
        "trade_count_30d": 20,  # Low activity
    }

    ai_analysis = {"risk_level": "HIGH", "max_drawdown": 0.25}

    warnings = leaderboard_service._identify_warnings(stats, ai_analysis)

    assert len(warnings) <= 2
    assert any("loss" in warning.lower() for warning in warnings)


@pytest.mark.asyncio
async def test_suggest_copy_size(leaderboard_service):
    """Test suggesting copy size"""
    stats = {"last_30d_volume_usd": 5000000}  # High volume

    ai_analysis = {"risk_level": "LOW", "optimal_copy_ratio": 0.15}

    size = leaderboard_service._suggest_copy_size(stats, ai_analysis)

    assert 10.0 <= size <= 1000.0  # Within reasonable bounds


@pytest.mark.asyncio
async def test_get_leaderboard_by_category_volume(leaderboard_service):
    """Test getting leaderboard by volume category"""
    # Mock top traders
    mock_traders = [
        {"address": "0xabc123", "last_30d_volume_usd": 1000000},
        {"address": "0xdef456", "last_30d_volume_usd": 2000000},
        {"address": "0xghi789", "last_30d_volume_usd": 500000},
    ]

    with patch.object(
        leaderboard_service, "get_top_traders", return_value=mock_traders
    ):
        traders = await leaderboard_service.get_leaderboard_by_category(
            "volume", limit=3
        )

        assert len(traders) == 3
        assert traders[0]["last_30d_volume_usd"] == 2000000  # Highest volume first


@pytest.mark.asyncio
async def test_get_leaderboard_by_category_pnl(leaderboard_service):
    """Test getting leaderboard by PnL category"""
    # Mock top traders
    mock_traders = [
        {"address": "0xabc123", "realized_pnl_clean_usd": 50000},
        {"address": "0xdef456", "realized_pnl_clean_usd": 100000},
        {"address": "0xghi789", "realized_pnl_clean_usd": 25000},
    ]

    with patch.object(
        leaderboard_service, "get_top_traders", return_value=mock_traders
    ):
        traders = await leaderboard_service.get_leaderboard_by_category("pnl", limit=3)

        assert len(traders) == 3
        assert traders[0]["realized_pnl_clean_usd"] == 100000  # Highest PnL first


@pytest.mark.asyncio
async def test_search_traders(leaderboard_service, mock_db_pool, mock_redis):
    """Test searching traders by address"""
    db_pool, conn = mock_db_pool

    query = "0xabc123"

    # Mock database response
    mock_rows = [
        {
            "address": "0xabc123def456",
            "last_30d_volume_usd": 1000000,
            "realized_pnl_clean_usd": 50000,
            "trade_count_30d": 500,
            "unique_symbols": 5,
        }
    ]

    conn.fetch.return_value = mock_rows
    mock_redis.get.return_value = None  # No cached AI analysis

    traders = await leaderboard_service.search_traders(query, limit=10)

    assert len(traders) == 1
    assert traders[0]["address"] == "0xabc123def456"
    assert "copyability_score" in traders[0]


@pytest.mark.asyncio
async def test_search_traders_invalid_query(leaderboard_service):
    """Test searching with invalid query"""
    query = "invalid"

    traders = await leaderboard_service.search_traders(query, limit=10)

    assert traders == []


@pytest.mark.asyncio
async def test_get_trader_analytics_summary(leaderboard_service, mock_db_pool):
    """Test getting trader analytics summary"""
    db_pool, conn = mock_db_pool

    # Mock database responses
    conn.fetchval.side_effect = [100, 50]  # total_traders, active_traders

    conn.fetchrow.return_value = {
        "avg_volume": 500000,
        "max_volume": 5000000,
        "min_volume": 10000,
    }

    conn.fetch.return_value = [
        {"archetype": "Conservative Scalper", "count": 30},
        {"archetype": "Risk Manager", "count": 25},
        {"archetype": "Volume Hunter", "count": 20},
    ]

    summary = await leaderboard_service.get_trader_analytics_summary()

    assert summary["total_traders"] == 100
    assert summary["active_traders"] == 50
    assert "volume_stats" in summary
    assert "archetype_distribution" in summary
    assert len(summary["archetype_distribution"]) == 3
