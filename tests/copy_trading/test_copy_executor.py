"""
Test Copy Execution Engine
Tests the copy trading execution and position management
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from src.copy_trading.copy_executor import CopyExecutor, CopyTradeRequest, CopyConfiguration

class TestCopyExecutor:
    @pytest.mark.asyncio
    async def test_should_copy_trade_filters(self):
        """Test trade filtering logic"""
        config = CopyConfiguration(
            copytrader_id=1,
            user_id=123,
            leader_address='0x1234567890123456789012345678901234567890',
            is_enabled=True,
            sizing_mode='FIXED_NOTIONAL',
            sizing_value=1000,
            max_slippage_bps=100,
            max_leverage=50,
            notional_cap=10000,
            pair_filters={'allowed': ['BTC-USD', 'ETH-USD']},
            tp_sl_policy={}
        )
        
        # Valid trade
        valid_trade = {
            'pair_symbol': 'BTC-USD',
            'size': 0.1,
            'price': 50000,
            'leverage': 10,
            'timestamp': datetime.utcnow()
        }
        
        # Invalid trades
        invalid_pair = {**valid_trade, 'pair_symbol': 'SOL-USD'}
        high_leverage = {**valid_trade, 'leverage': 100}
        too_large = {**valid_trade, 'size': 1.0}  # $50k notional
        old_trade = {**valid_trade, 'timestamp': datetime.utcnow() - timedelta(minutes=10)}
        
        executor = CopyExecutor(None, None, None, None, None)
        
        # Mock market intelligence
        executor.market_intel = AsyncMock()
        executor.market_intel.get_copy_timing_signal.return_value = MagicMock(signal='green')
        
        assert await executor._should_copy_trade(config, valid_trade) == True
        assert await executor._should_copy_trade(config, invalid_pair) == False
        assert await executor._should_copy_trade(config, high_leverage) == False
        assert await executor._should_copy_trade(config, too_large) == False
        assert await executor._should_copy_trade(config, old_trade) == False
    
    @pytest.mark.asyncio
    async def test_copy_sizing_calculation(self):
        """Test copy sizing calculations"""
        trade = {'size': 1.0, 'price': 50000}  # $50k notional
        
        # Fixed sizing
        config_fixed = CopyConfiguration(
            copytrader_id=1,
            user_id=123,
            leader_address='0x123',
            is_enabled=True,
            sizing_mode='FIXED_NOTIONAL',
            sizing_value=1000,
            max_slippage_bps=100,
            max_leverage=50,
            notional_cap=10000,
            pair_filters={},
            tp_sl_policy={}
        )
        
        executor = CopyExecutor(None, None, None, None, None)
        request = await executor._create_copy_request(config_fixed, trade)
        
        expected_size = 1000 / 50000  # $1k / $50k price = 0.02
        assert abs(request.target_size - expected_size) < 0.001
        
        # Percentage sizing
        config_pct = CopyConfiguration(
            copytrader_id=1,
            user_id=123,
            leader_address='0x123',
            is_enabled=True,
            sizing_mode='PCT_EQUITY',
            sizing_value=5,
            max_slippage_bps=100,
            max_leverage=50,
            notional_cap=10000,
            pair_filters={},
            tp_sl_policy={}
        )
        
        executor._get_user_balance = AsyncMock(return_value=20000)  # Mock balance
        
        request = await executor._create_copy_request(config_pct, trade)
        expected_size = (20000 * 0.05) / 50000  # 5% of $20k = 0.02
        assert abs(request.target_size - expected_size) < 0.001
    
    @pytest.mark.asyncio
    async def test_config_validation(self):
        """Test copy configuration validation"""
        executor = CopyExecutor(None, None, None, None, None)
        
        # Valid config
        valid_config = {
            'sizing_mode': 'FIXED_NOTIONAL',
            'sizing_value': 100,
            'max_slippage_bps': 100,
            'max_leverage': 50
        }
        
        result = await executor._validate_copy_config(valid_config)
        assert result['valid'] == True
        
        # Invalid configs
        invalid_configs = [
            {'sizing_mode': 'INVALID'},  # Invalid sizing mode
            {'sizing_mode': 'FIXED_NOTIONAL', 'sizing_value': -100},  # Negative value
            {'sizing_mode': 'PCT_EQUITY', 'sizing_value': 150},  # >100%
            {}  # Missing required fields
        ]
        
        for config in invalid_configs:
            result = await executor._validate_copy_config(config)
            assert result['valid'] == False
            assert 'error' in result
    
    @pytest.mark.asyncio
    async def test_follow_trader_flow(self):
        """Test follow trader flow"""
        executor = CopyExecutor(None, None, None, None, None)
        
        # Mock database operations
        executor.db_pool = AsyncMock()
        conn = AsyncMock()
        executor.db_pool.acquire.return_value.__aenter__.return_value = conn
        
        # Mock user balance
        executor._get_user_balance = AsyncMock(return_value=10000)
        
        # Test follow trader
        config = {
            'name': 'Test Copytrader',
            'sizing_mode': 'FIXED_NOTIONAL',
            'sizing_value': 100,
            'max_slippage_bps': 100,
            'max_leverage': 50
        }
        
        result = await executor.follow_trader(123, '0x1234567890123456789012345678901234567890', config)
        
        assert result['success'] == True
        assert 'copytrader_id' in result
        assert 'message' in result
    
    @pytest.mark.asyncio
    async def test_unfollow_trader_flow(self):
        """Test unfollow trader flow"""
        executor = CopyExecutor(None, None, None, None, None)
        
        # Mock database operations
        executor.db_pool = AsyncMock()
        conn = AsyncMock()
        executor.db_pool.acquire.return_value.__aenter__.return_value = conn
        
        result = await executor.unfollow_trader(123, '0x1234567890123456789012345678901234567890')
        
        assert result['success'] == True
        assert 'message' in result
    
    @pytest.mark.asyncio
    async def test_get_copy_status(self):
        """Test get copy status"""
        executor = CopyExecutor(None, None, None, None, None)
        
        # Mock database operations
        executor.db_pool = AsyncMock()
        conn = AsyncMock()
        executor.db_pool.acquire.return_value.__aenter__.return_value = conn
        
        # Mock query results
        conn.fetch.return_value = [
            {'id': 1, 'name': 'Test Copytrader', 'is_enabled': True, 'sizing_mode': 'FIXED_NOTIONAL', 'sizing_value': 100, 'max_leverage': 50},
            {'leader_address': '0x123', 'started_at': datetime.utcnow(), 'is_active': True, 'last_30d_volume_usd': 1000000, 'realized_pnl_clean_usd': 50000},
            {'leader_address': '0x123', 'status': 'OPEN', 'opened_at': datetime.utcnow(), 'pnl_usd': 100}
        ]
        
        # Mock manual PnL calculation
        executor._calculate_manual_pnl = AsyncMock(return_value=1000)
        
        status = await executor.get_copy_status(123)
        
        assert 'profiles' in status
        assert 'following' in status
        assert 'recent_positions' in status
        assert 'performance' in status
        assert status['performance']['manual_pnl'] == 1000
    
    @pytest.mark.asyncio
    async def test_execute_copy_trade_success(self):
        """Test successful copy trade execution"""
        executor = CopyExecutor(None, None, None, None, None)
        
        # Mock dependencies
        executor._get_current_price = AsyncMock(return_value=50000)
        executor._execute_avantis_trade = AsyncMock(return_value='0xmocktxhash')
        executor._get_user_id = AsyncMock(return_value=123)
        executor._get_max_leverage = AsyncMock(return_value=50)
        executor._record_copy_position = AsyncMock()
        executor._send_copy_notification = AsyncMock()
        
        # Create copy request
        request = CopyTradeRequest(
            copytrader_id=1,
            leader_address='0x123',
            trade_data={'pair_symbol': 'BTC-USD', 'price': 50000, 'is_long': True, 'leverage': 10},
            original_size=1.0,
            target_size=0.1,
            max_slippage_bps=100
        )
        
        await executor._execute_copy_trade(request)
        
        # Verify execution
        executor._execute_avantis_trade.assert_called_once()
        executor._record_copy_position.assert_called_once()
        executor._send_copy_notification.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_copy_trade_slippage_failure(self):
        """Test copy trade execution with slippage failure"""
        executor = CopyExecutor(None, None, None, None, None)
        
        # Mock dependencies
        executor._get_current_price = AsyncMock(return_value=60000)  # High slippage
        executor._record_copy_position = AsyncMock()
        executor._send_copy_notification = AsyncMock()
        
        # Create copy request
        request = CopyTradeRequest(
            copytrader_id=1,
            leader_address='0x123',
            trade_data={'pair_symbol': 'BTC-USD', 'price': 50000, 'is_long': True, 'leverage': 10},
            original_size=1.0,
            target_size=0.1,
            max_slippage_bps=100  # 1% max slippage
        )
        
        await executor._execute_copy_trade(request)
        
        # Verify failure due to slippage
        executor._record_copy_position.assert_called_once()
        args, kwargs = executor._record_copy_position.call_args
        assert kwargs['status'] == 'FAILED'
        assert 'Slippage exceeded' in kwargs['reason']
    
    @pytest.mark.asyncio
    async def test_execute_copy_trade_execution_failure(self):
        """Test copy trade execution with execution failure"""
        executor = CopyExecutor(None, None, None, None, None)
        
        # Mock dependencies
        executor._get_current_price = AsyncMock(return_value=50000)
        executor._execute_avantis_trade = AsyncMock(side_effect=Exception("Execution failed"))
        executor._get_user_id = AsyncMock(return_value=123)
        executor._get_max_leverage = AsyncMock(return_value=50)
        executor._record_copy_position = AsyncMock()
        executor._send_copy_notification = AsyncMock()
        
        # Create copy request
        request = CopyTradeRequest(
            copytrader_id=1,
            leader_address='0x123',
            trade_data={'pair_symbol': 'BTC-USD', 'price': 50000, 'is_long': True, 'leverage': 10},
            original_size=1.0,
            target_size=0.1,
            max_slippage_bps=100
        )
        
        await executor._execute_copy_trade(request)
        
        # Verify failure
        executor._record_copy_position.assert_called_once()
        args, kwargs = executor._record_copy_position.call_args
        assert kwargs['status'] == 'FAILED'
        assert 'Execution failed' in kwargs['reason']
    
    @pytest.mark.asyncio
    async def test_get_active_copy_configs(self):
        """Test getting active copy configurations"""
        executor = CopyExecutor(None, None, None, None, None)
        
        # Mock database operations
        executor.db_pool = AsyncMock()
        conn = AsyncMock()
        executor.db_pool.acquire.return_value.__aenter__.return_value = conn
        
        # Mock query results
        conn.fetch.return_value = [
            {
                'copytrader_id': 1,
                'user_id': 123,
                'leader_address': '0x123',
                'is_active': True,
                'sizing_mode': 'FIXED_NOTIONAL',
                'sizing_value': 100,
                'max_slippage_bps': 100,
                'max_leverage': 50,
                'notional_cap': 10000,
                'pair_filters': {},
                'tp_sl_policy': {}
            }
        ]
        
        configs = await executor._get_active_copy_configs()
        
        assert len(configs) == 1
        assert isinstance(configs[0], CopyConfiguration)
        assert configs[0].copytrader_id == 1
        assert configs[0].user_id == 123
        assert configs[0].leader_address == '0x123'
        assert configs[0].is_enabled == True
    
    @pytest.mark.asyncio
    async def test_get_new_leader_trades(self):
        """Test getting new leader trades"""
        executor = CopyExecutor(None, None, None, None, None)
        
        # Mock database operations
        executor.db_pool = AsyncMock()
        conn = AsyncMock()
        executor.db_pool.acquire.return_value.__aenter__.return_value = conn
        
        # Mock query results
        conn.fetch.return_value = [
            {
                'address': '0x123',
                'pair_symbol': 'BTC-USD',
                'size': 1.0,
                'price': 50000,
                'is_long': True,
                'leverage': 10,
                'event_type': 'OPENED',
                'timestamp': datetime.utcnow()
            }
        ]
        
        trades = await executor._get_new_leader_trades('0x123', since='2024-01-01T00:00:00')
        
        assert len(trades) == 1
        assert trades[0]['address'] == '0x123'
        assert trades[0]['pair_symbol'] == 'BTC-USD'
    
    @pytest.mark.asyncio
    async def test_check_leader_activity(self):
        """Test checking leader activity"""
        executor = CopyExecutor(None, None, None, None, None)
        
        # Mock dependencies
        executor.redis = AsyncMock()
        executor.redis.get.return_value = None
        executor.redis.set.return_value = None
        executor._get_new_leader_trades = AsyncMock(return_value=[])
        executor._should_copy_trade = AsyncMock(return_value=False)
        executor._create_copy_request = AsyncMock()
        executor.execution_queue = AsyncMock()
        
        config = CopyConfiguration(
            copytrader_id=1,
            user_id=123,
            leader_address='0x123',
            is_enabled=True,
            sizing_mode='FIXED_NOTIONAL',
            sizing_value=100,
            max_slippage_bps=100,
            max_leverage=50,
            notional_cap=10000,
            pair_filters={},
            tp_sl_policy={}
        )
        
        await executor._check_leader_activity(config)
        
        # Verify Redis operations
        executor.redis.get.assert_called_once()
        executor.redis.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_concurrent_copy_execution(self):
        """Test handling multiple copy requests simultaneously"""
        executor = CopyExecutor(None, None, None, None, None)
        
        # Mock successful execution
        executor._get_current_price = AsyncMock(return_value=50000)
        executor._execute_avantis_trade = AsyncMock(return_value='0xmocktxhash')
        executor._get_user_id = AsyncMock(return_value=123)
        executor._get_max_leverage = AsyncMock(return_value=50)
        executor._record_copy_position = AsyncMock()
        executor._send_copy_notification = AsyncMock()
        
        # Create 10 concurrent copy requests
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
        
        # Execute all requests concurrently
        tasks = [executor._execute_copy_trade(req) for req in requests]
        await asyncio.gather(*tasks)
        
        # Verify all executions
        assert executor._execute_avantis_trade.call_count == 10
        assert executor._record_copy_position.call_count == 10
        assert executor._send_copy_notification.call_count == 10
