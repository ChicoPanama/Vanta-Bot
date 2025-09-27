"""
Tests for Copy Executor functionality
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.copy_trading.copy_executor import CopyExecutor, CopyStatus, CopyConfiguration
from src.analytics.position_tracker import TraderStats

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
def mock_avantis_client():
    """Mock Avantis client"""
    return AsyncMock()

@pytest.fixture
def mock_market_intelligence():
    """Mock market intelligence"""
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
def copy_executor(mock_db_pool, mock_redis, mock_avantis_client, mock_market_intelligence, mock_config):
    """Create CopyExecutor instance with mocks"""
    db_pool, _ = mock_db_pool
    return CopyExecutor(
        db_pool=db_pool,
        redis_client=mock_redis,
        avantis_client=mock_avantis_client,
        market_intelligence=mock_market_intelligence,
        config=mock_config
    )

@pytest.mark.asyncio
async def test_copy_executor_initialization(copy_executor):
    """Test CopyExecutor initialization"""
    assert copy_executor is not None
    assert not copy_executor.is_running
    assert copy_executor.active_copytraders == set()

@pytest.mark.asyncio
async def test_get_active_copy_configs(copy_executor, mock_db_pool):
    """Test getting active copy configurations"""
    db_pool, conn = mock_db_pool
    
    # Mock database response
    mock_rows = [
        {
            'copytrader_id': 1,
            'user_id': 123,
            'is_enabled': True,
            'sizing_mode': 'FIXED_NOTIONAL',
            'sizing_value': 100.0,
            'max_slippage_bps': 100,
            'max_leverage': 50.0,
            'notional_cap': 1000.0,
            'pair_filters': {}
        }
    ]
    
    conn.fetch.return_value = mock_rows
    
    configs = await copy_executor._get_active_copy_configs()
    
    assert len(configs) == 1
    assert configs[0].copytrader_id == 1
    assert configs[0].user_id == 123
    assert configs[0].sizing_mode == 'FIXED_NOTIONAL'
    assert configs[0].sizing_value == 100.0

@pytest.mark.asyncio
async def test_should_copy_trade_green_regime(copy_executor):
    """Test trade should be copied when market regime is green"""
    config = CopyConfiguration(
        copytrader_id=1,
        user_id=123,
        sizing_mode='FIXED_NOTIONAL',
        sizing_value=100.0,
        max_slippage_bps=100,
        max_leverage=50.0,
        notional_cap=1000.0,
        pair_filters={},
        is_enabled=True
    )
    
    trade = {
        'pair': '0',
        'size': 1.0,
        'price': 50000.0,
        'leverage': 10,
        'is_long': True
    }
    
    # Mock green market regime
    mock_signal = MagicMock()
    mock_signal.signal = 'green'
    copy_executor.market_intel.get_copy_timing_signal.return_value = mock_signal
    
    should_copy = await copy_executor._should_copy_trade(config, trade)
    
    assert should_copy is True

@pytest.mark.asyncio
async def test_should_copy_trade_red_regime(copy_executor):
    """Test trade should not be copied when market regime is red"""
    config = CopyConfiguration(
        copytrader_id=1,
        user_id=123,
        sizing_mode='FIXED_NOTIONAL',
        sizing_value=100.0,
        max_slippage_bps=100,
        max_leverage=50.0,
        notional_cap=1000.0,
        pair_filters={},
        is_enabled=True
    )
    
    trade = {
        'pair': '0',
        'size': 1.0,
        'price': 50000.0,
        'leverage': 10,
        'is_long': True
    }
    
    # Mock red market regime
    mock_signal = MagicMock()
    mock_signal.signal = 'red'
    copy_executor.market_intel.get_copy_timing_signal.return_value = mock_signal
    
    should_copy = await copy_executor._should_copy_trade(config, trade)
    
    assert should_copy is False

@pytest.mark.asyncio
async def test_should_copy_trade_leverage_limit(copy_executor):
    """Test trade should not be copied when leverage exceeds limit"""
    config = CopyConfiguration(
        copytrader_id=1,
        user_id=123,
        sizing_mode='FIXED_NOTIONAL',
        sizing_value=100.0,
        max_slippage_bps=100,
        max_leverage=50.0,
        notional_cap=1000.0,
        pair_filters={},
        is_enabled=True
    )
    
    trade = {
        'pair': '0',
        'size': 1.0,
        'price': 50000.0,
        'leverage': 100,  # Exceeds limit
        'is_long': True
    }
    
    # Mock green market regime
    mock_signal = MagicMock()
    mock_signal.signal = 'green'
    copy_executor.market_intel.get_copy_timing_signal.return_value = mock_signal
    
    should_copy = await copy_executor._should_copy_trade(config, trade)
    
    assert should_copy is False

@pytest.mark.asyncio
async def test_should_copy_trade_pair_filter(copy_executor):
    """Test trade should not be copied when pair is filtered out"""
    config = CopyConfiguration(
        copytrader_id=1,
        user_id=123,
        sizing_mode='FIXED_NOTIONAL',
        sizing_value=100.0,
        max_slippage_bps=100,
        max_leverage=50.0,
        notional_cap=1000.0,
        pair_filters={'allowed': ['1', '2']},  # Only allow pairs 1 and 2
        is_enabled=True
    )
    
    trade = {
        'pair': '0',  # Not in allowed list
        'size': 1.0,
        'price': 50000.0,
        'leverage': 10,
        'is_long': True
    }
    
    # Mock green market regime
    mock_signal = MagicMock()
    mock_signal.signal = 'green'
    copy_executor.market_intel.get_copy_timing_signal.return_value = mock_signal
    
    should_copy = await copy_executor._should_copy_trade(config, trade)
    
    assert should_copy is False

@pytest.mark.asyncio
async def test_create_copy_request_fixed_notional(copy_executor):
    """Test creating copy request with fixed notional sizing"""
    config = CopyConfiguration(
        copytrader_id=1,
        user_id=123,
        sizing_mode='FIXED_NOTIONAL',
        sizing_value=100.0,
        max_slippage_bps=100,
        max_leverage=50.0,
        notional_cap=1000.0,
        pair_filters={},
        is_enabled=True
    )
    
    trade = {
        'pair': '0',
        'size': 2.0,
        'price': 50000.0,
        'leverage': 10,
        'is_long': True,
        'timestamp': datetime.utcnow(),
        'block_number': 12345,
        'tx_hash': '0x123'
    }
    
    leader_address = '0xabc123'
    
    # Mock user balance
    copy_executor._get_user_balance = AsyncMock(return_value=1000.0)
    
    request = await copy_executor._create_copy_request(config, trade, leader_address)
    
    assert request.copytrader_id == 1
    assert request.leader_address == leader_address
    assert request.original_size == 2.0
    assert request.target_size == 100.0 / 50000.0  # $100 / $50k
    assert request.max_slippage_bps == 100

@pytest.mark.asyncio
async def test_create_copy_request_percentage_sizing(copy_executor):
    """Test creating copy request with percentage sizing"""
    config = CopyConfiguration(
        copytrader_id=1,
        user_id=123,
        sizing_mode='PCT_EQUITY',
        sizing_value=5.0,  # 5%
        max_slippage_bps=100,
        max_leverage=50.0,
        notional_cap=1000.0,
        pair_filters={},
        is_enabled=True
    )
    
    trade = {
        'pair': '0',
        'size': 2.0,
        'price': 50000.0,
        'leverage': 10,
        'is_long': True,
        'timestamp': datetime.utcnow(),
        'block_number': 12345,
        'tx_hash': '0x123'
    }
    
    leader_address = '0xabc123'
    
    # Mock user balance
    copy_executor._get_user_balance = AsyncMock(return_value=1000.0)
    
    request = await copy_executor._create_copy_request(config, trade, leader_address)
    
    assert request.copytrader_id == 1
    assert request.leader_address == leader_address
    assert request.original_size == 2.0
    assert request.target_size == (1000.0 * 0.05) / 50000.0  # 5% of $1000 / $50k
    assert request.max_slippage_bps == 100

@pytest.mark.asyncio
async def test_execute_copy_trade_success(copy_executor):
    """Test successful copy trade execution"""
    from src.copy_trading.copy_executor import CopyTradeRequest
    
    request = CopyTradeRequest(
        copytrader_id=1,
        leader_address='0xabc123',
        trade_data={
            'pair': '0',
            'size': 1.0,
            'price': 50000.0,
            'leverage': 10,
            'is_long': True
        },
        original_size=1.0,
        target_size=0.002,  # $100 / $50k
        max_slippage_bps=100
    )
    
    # Mock successful execution
    copy_executor._get_current_price = AsyncMock(return_value=50000.0)
    copy_executor._get_user_id = AsyncMock(return_value=123)
    copy_executor._get_max_leverage = AsyncMock(return_value=50.0)
    copy_executor._execute_avantis_trade = AsyncMock(return_value='0xsuccess')
    copy_executor._record_copy_position = AsyncMock()
    copy_executor._send_copy_notification = AsyncMock()
    
    await copy_executor._execute_copy_trade(request)
    
    # Verify execution was called
    copy_executor._execute_avantis_trade.assert_called_once()
    copy_executor._record_copy_position.assert_called_once()
    copy_executor._send_copy_notification.assert_called_once()

@pytest.mark.asyncio
async def test_execute_copy_trade_slippage_exceeded(copy_executor):
    """Test copy trade execution with excessive slippage"""
    from src.copy_trading.copy_executor import CopyTradeRequest
    
    request = CopyTradeRequest(
        copytrader_id=1,
        leader_address='0xabc123',
        trade_data={
            'pair': '0',
            'size': 1.0,
            'price': 50000.0,
            'leverage': 10,
            'is_long': True
        },
        original_size=1.0,
        target_size=0.002,
        max_slippage_bps=100
    )
    
    # Mock high slippage (2% > 1% limit)
    copy_executor._get_current_price = AsyncMock(return_value=51000.0)  # 2% higher
    copy_executor._record_copy_position = AsyncMock()
    copy_executor._send_copy_notification = AsyncMock()
    
    await copy_executor._execute_copy_trade(request)
    
    # Verify trade was rejected due to slippage
    copy_executor._record_copy_position.assert_called_once_with(
        request, CopyStatus.FAILED, reason='Slippage exceeded'
    )

@pytest.mark.asyncio
async def test_follow_trader_success(copy_executor, mock_db_pool):
    """Test successful trader following"""
    db_pool, conn = mock_db_pool
    
    user_id = 123
    leader_address = '0xabc123'
    config = {
        'sizing_mode': 'FIXED_NOTIONAL',
        'sizing_value': 100.0,
        'max_slippage_bps': 100,
        'max_leverage': 50.0,
        'notional_cap': 1000.0
    }
    
    # Mock database responses
    conn.fetchrow.return_value = None  # No existing profile
    conn.fetchval.return_value = 1  # New copytrader ID
    conn.execute.return_value = None
    
    result = await copy_executor.follow_trader(user_id, leader_address, config)
    
    assert result['success'] is True
    assert 'copytrader_id' in result
    assert 'message' in result

@pytest.mark.asyncio
async def test_follow_trader_invalid_config(copy_executor):
    """Test trader following with invalid configuration"""
    user_id = 123
    leader_address = '0xabc123'
    config = {
        'sizing_mode': 'INVALID_MODE',
        'sizing_value': 100.0
    }
    
    result = await copy_executor.follow_trader(user_id, leader_address, config)
    
    assert result['success'] is False
    assert 'error' in result

@pytest.mark.asyncio
async def test_unfollow_trader_success(copy_executor, mock_db_pool):
    """Test successful trader unfollowing"""
    db_pool, conn = mock_db_pool
    
    user_id = 123
    leader_address = '0xabc123'
    
    conn.execute.return_value = None
    
    result = await copy_executor.unfollow_trader(user_id, leader_address)
    
    assert result['success'] is True
    assert 'message' in result

@pytest.mark.asyncio
async def test_get_copy_status(copy_executor, mock_db_pool):
    """Test getting copy trading status"""
    db_pool, conn = mock_db_pool
    
    user_id = 123
    
    # Mock database responses
    conn.fetch.return_value = []  # No profiles
    copy_executor._calculate_manual_pnl = AsyncMock(return_value=0.0)
    
    status = await copy_executor.get_copy_status(user_id)
    
    assert 'profiles' in status
    assert 'following' in status
    assert 'recent_positions' in status
    assert 'performance' in status
    assert status['performance']['manual_pnl'] == 0.0
    assert status['performance']['copy_pnl'] == 0.0

@pytest.mark.asyncio
async def test_validate_copy_config_valid(copy_executor):
    """Test valid copy configuration validation"""
    config = {
        'sizing_mode': 'FIXED_NOTIONAL',
        'sizing_value': 100.0,
        'max_slippage_bps': 100,
        'max_leverage': 50.0
    }
    
    result = await copy_executor._validate_copy_config(config)
    
    assert result['valid'] is True

@pytest.mark.asyncio
async def test_validate_copy_config_invalid_sizing_mode(copy_executor):
    """Test invalid sizing mode validation"""
    config = {
        'sizing_mode': 'INVALID_MODE',
        'sizing_value': 100.0
    }
    
    result = await copy_executor._validate_copy_config(config)
    
    assert result['valid'] is False
    assert 'error' in result

@pytest.mark.asyncio
async def test_validate_copy_config_invalid_percentage(copy_executor):
    """Test invalid percentage validation"""
    config = {
        'sizing_mode': 'PCT_EQUITY',
        'sizing_value': 50.0  # Too high
    }
    
    result = await copy_executor._validate_copy_config(config)
    
    assert result['valid'] is False
    assert 'error' in result

@pytest.mark.asyncio
async def test_get_symbol_from_pair(copy_executor):
    """Test symbol mapping from pair"""
    assert copy_executor._get_symbol_from_pair('0') == 'BTC-USD'
    assert copy_executor._get_symbol_from_pair('1') == 'ETH-USD'
    assert copy_executor._get_symbol_from_pair('2') == 'SOL-USD'
    assert copy_executor._get_symbol_from_pair('3') == 'AVAX-USD'
    assert copy_executor._get_symbol_from_pair('999') == 'BTC-USD'  # Default