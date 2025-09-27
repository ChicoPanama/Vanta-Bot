"""
Test feature flags system
"""
import os
import pytest
from unittest.mock import patch

from src.config.flags import FeatureFlags, ExecutionMode, flags


class TestFeatureFlags:
    """Test feature flags system"""
    
    def test_flags_initialization(self):
        """Test that flags initialize with default values"""
        flags_obj = FeatureFlags()
        
        # Test default values
        assert flags_obj.execution_mode() == ExecutionMode.DRY
        assert flags_obj.is_dry_mode() is True
        assert flags_obj.is_live_mode() is False
        assert flags_obj.is_emergency_stopped() is False
        assert flags_obj.is_maintenance_mode() is False
    
    def test_execution_mode_environment(self):
        """Test execution mode from environment"""
        with patch.dict(os.environ, {'COPY_EXECUTION_MODE': 'LIVE'}):
            flags_obj = FeatureFlags()
            
            assert flags_obj.execution_mode() == ExecutionMode.LIVE
            assert flags_obj.is_dry_mode() is False
            assert flags_obj.is_live_mode() is True
    
    def test_emergency_controls(self):
        """Test emergency control flags"""
        with patch.dict(os.environ, {
            'EMERGENCY_STOP': 'true',
            'EMERGENCY_STOP_COPY_TRADING': 'true',
            'PAUSE_NEW_FOLLOWS': 'true',
            'MAINTENANCE_MODE': 'true'
        }):
            flags_obj = FeatureFlags()
            
            assert flags_obj.is_emergency_stopped() is True
            assert flags_obj.is_copy_trading_stopped() is True
            assert flags_obj.can_follow_new_leaders() is False
            assert flags_obj.is_maintenance_mode() is True
    
    def test_feature_toggles(self):
        """Test feature toggle flags"""
        with patch.dict(os.environ, {
            'ENABLE_COPY_TRADING': 'false',
            'ENABLE_AI_ANALYSIS': 'false',
            'ENABLE_MARKET_INTELLIGENCE': 'false',
            'ENABLE_LEADERBOARD': 'false',
            'ENABLE_TELEGRAM_COMMANDS': 'false'
        }):
            flags_obj = FeatureFlags()
            
            assert flags_obj.is_feature_enabled('enable_copy_trading') is False
            assert flags_obj.is_feature_enabled('enable_ai_analysis') is False
            assert flags_obj.is_feature_enabled('enable_market_intelligence') is False
            assert flags_obj.is_feature_enabled('enable_leaderboard') is False
            assert flags_obj.is_feature_enabled('enable_telegram_commands') is False
    
    def test_trading_features(self):
        """Test trading feature flags"""
        with patch.dict(os.environ, {
            'ENABLE_MARKET_ORDERS': 'false',
            'ENABLE_LIMIT_ORDERS': 'true',
            'ENABLE_STOP_ORDERS': 'true'
        }):
            flags_obj = FeatureFlags()
            
            assert flags_obj.is_feature_enabled('enable_market_orders') is False
            assert flags_obj.is_feature_enabled('enable_limit_orders') is True
            assert flags_obj.is_feature_enabled('enable_stop_orders') is True
    
    def test_risk_management(self):
        """Test risk management flags"""
        with patch.dict(os.environ, {
            'ENABLE_SLIPPAGE_PROTECTION': 'false',
            'ENABLE_POSITION_LIMITS': 'false',
            'ENABLE_LEVERAGE_LIMITS': 'false'
        }):
            flags_obj = FeatureFlags()
            
            assert flags_obj.is_feature_enabled('enable_slippage_protection') is False
            assert flags_obj.is_feature_enabled('enable_position_limits') is False
            assert flags_obj.is_feature_enabled('enable_leverage_limits') is False
    
    def test_can_execute_trades(self):
        """Test trade execution permission logic"""
        # Normal conditions
        with patch.dict(os.environ, {
            'EMERGENCY_STOP': 'false',
            'MAINTENANCE_MODE': 'false',
            'ENABLE_COPY_TRADING': 'true',
            'ENABLE_MARKET_ORDERS': 'true'
        }):
            flags_obj = FeatureFlags()
            assert flags_obj.can_execute_trades() is True
        
        # Emergency stop
        with patch.dict(os.environ, {
            'EMERGENCY_STOP': 'true',
            'MAINTENANCE_MODE': 'false',
            'ENABLE_COPY_TRADING': 'true',
            'ENABLE_MARKET_ORDERS': 'true'
        }):
            flags_obj = FeatureFlags()
            assert flags_obj.can_execute_trades() is False
        
        # Maintenance mode
        with patch.dict(os.environ, {
            'EMERGENCY_STOP': 'false',
            'MAINTENANCE_MODE': 'true',
            'ENABLE_COPY_TRADING': 'true',
            'ENABLE_MARKET_ORDERS': 'true'
        }):
            flags_obj = FeatureFlags()
            assert flags_obj.can_execute_trades() is False
        
        # Copy trading disabled
        with patch.dict(os.environ, {
            'EMERGENCY_STOP': 'false',
            'MAINTENANCE_MODE': 'false',
            'ENABLE_COPY_TRADING': 'false',
            'ENABLE_MARKET_ORDERS': 'true'
        }):
            flags_obj = FeatureFlags()
            assert flags_obj.can_execute_trades() is False
        
        # Market orders disabled
        with patch.dict(os.environ, {
            'EMERGENCY_STOP': 'false',
            'MAINTENANCE_MODE': 'false',
            'ENABLE_COPY_TRADING': 'true',
            'ENABLE_MARKET_ORDERS': 'false'
        }):
            flags_obj = FeatureFlags()
            assert flags_obj.can_execute_trades() is False
    
    def test_can_copy_trade(self):
        """Test copy trading permission logic"""
        # Normal conditions
        with patch.dict(os.environ, {
            'EMERGENCY_STOP': 'false',
            'EMERGENCY_STOP_COPY_TRADING': 'false',
            'MAINTENANCE_MODE': 'false',
            'PAUSE_NEW_FOLLOWS': 'false',
            'ENABLE_COPY_TRADING': 'true'
        }):
            flags_obj = FeatureFlags()
            assert flags_obj.can_copy_trade() is True
        
        # Emergency stop
        with patch.dict(os.environ, {
            'EMERGENCY_STOP': 'true',
            'EMERGENCY_STOP_COPY_TRADING': 'false',
            'MAINTENANCE_MODE': 'false',
            'PAUSE_NEW_FOLLOWS': 'false',
            'ENABLE_COPY_TRADING': 'true'
        }):
            flags_obj = FeatureFlags()
            assert flags_obj.can_copy_trade() is False
        
        # Copy trading emergency stop
        with patch.dict(os.environ, {
            'EMERGENCY_STOP': 'false',
            'EMERGENCY_STOP_COPY_TRADING': 'true',
            'MAINTENANCE_MODE': 'false',
            'PAUSE_NEW_FOLLOWS': 'false',
            'ENABLE_COPY_TRADING': 'true'
        }):
            flags_obj = FeatureFlags()
            assert flags_obj.can_copy_trade() is False
    
    def test_can_follow_new_leaders(self):
        """Test new leader follow permission logic"""
        # Normal conditions
        with patch.dict(os.environ, {
            'EMERGENCY_STOP': 'false',
            'PAUSE_NEW_FOLLOWS': 'false',
            'MAINTENANCE_MODE': 'false',
            'ENABLE_COPY_TRADING': 'true'
        }):
            flags_obj = FeatureFlags()
            assert flags_obj.can_follow_new_leaders() is True
        
        # Pause new follows
        with patch.dict(os.environ, {
            'EMERGENCY_STOP': 'false',
            'PAUSE_NEW_FOLLOWS': 'true',
            'MAINTENANCE_MODE': 'false',
            'ENABLE_COPY_TRADING': 'true'
        }):
            flags_obj = FeatureFlags()
            assert flags_obj.can_follow_new_leaders() is False
    
    def test_can_use_ai_features(self):
        """Test AI features permission logic"""
        # Normal conditions
        with patch.dict(os.environ, {
            'MAINTENANCE_MODE': 'false',
            'ENABLE_AI_ANALYSIS': 'true',
            'ENABLE_MARKET_INTELLIGENCE': 'true'
        }):
            flags_obj = FeatureFlags()
            assert flags_obj.can_use_ai_features() is True
        
        # Maintenance mode
        with patch.dict(os.environ, {
            'MAINTENANCE_MODE': 'true',
            'ENABLE_AI_ANALYSIS': 'true',
            'ENABLE_MARKET_INTELLIGENCE': 'true'
        }):
            flags_obj = FeatureFlags()
            assert flags_obj.can_use_ai_features() is False
        
        # AI analysis disabled
        with patch.dict(os.environ, {
            'MAINTENANCE_MODE': 'false',
            'ENABLE_AI_ANALYSIS': 'false',
            'ENABLE_MARKET_INTELLIGENCE': 'true'
        }):
            flags_obj = FeatureFlags()
            assert flags_obj.can_use_ai_features() is False
    
    def test_can_show_leaderboard(self):
        """Test leaderboard permission logic"""
        # Normal conditions
        with patch.dict(os.environ, {
            'MAINTENANCE_MODE': 'false',
            'ENABLE_LEADERBOARD': 'true'
        }):
            flags_obj = FeatureFlags()
            assert flags_obj.can_show_leaderboard() is True
        
        # Maintenance mode
        with patch.dict(os.environ, {
            'MAINTENANCE_MODE': 'true',
            'ENABLE_LEADERBOARD': 'true'
        }):
            flags_obj = FeatureFlags()
            assert flags_obj.can_show_leaderboard() is False
        
        # Leaderboard disabled
        with patch.dict(os.environ, {
            'MAINTENANCE_MODE': 'false',
            'ENABLE_LEADERBOARD': 'false'
        }):
            flags_obj = FeatureFlags()
            assert flags_obj.can_show_leaderboard() is False
    
    def test_can_process_telegram_commands(self):
        """Test Telegram commands permission logic"""
        # Normal conditions
        with patch.dict(os.environ, {
            'MAINTENANCE_MODE': 'false',
            'ENABLE_TELEGRAM_COMMANDS': 'true'
        }):
            flags_obj = FeatureFlags()
            assert flags_obj.can_process_telegram_commands() is True
        
        # Maintenance mode
        with patch.dict(os.environ, {
            'MAINTENANCE_MODE': 'true',
            'ENABLE_TELEGRAM_COMMANDS': 'true'
        }):
            flags_obj = FeatureFlags()
            assert flags_obj.can_process_telegram_commands() is False
    
    def test_get_slippage_tolerance(self):
        """Test slippage tolerance based on mode"""
        # Dry mode
        with patch.dict(os.environ, {'COPY_EXECUTION_MODE': 'DRY'}):
            flags_obj = FeatureFlags()
            assert flags_obj.get_slippage_tolerance() == 5.0
        
        # Live mode
        with patch.dict(os.environ, {
            'COPY_EXECUTION_MODE': 'LIVE',
            'DEFAULT_SLIPPAGE_PCT': '2.0'
        }):
            flags_obj = FeatureFlags()
            assert flags_obj.get_slippage_tolerance() == 2.0
    
    def test_get_max_leverage(self):
        """Test maximum leverage based on mode and flags"""
        # Dry mode with leverage limits
        with patch.dict(os.environ, {
            'COPY_EXECUTION_MODE': 'DRY',
            'ENABLE_LEVERAGE_LIMITS': 'true',
            'MAX_LEVERAGE': '500',
            'MAX_COPY_LEVERAGE': '100'
        }):
            flags_obj = FeatureFlags()
            assert flags_obj.get_max_leverage() == 100  # Lower limit in dry mode
        
        # Live mode with leverage limits
        with patch.dict(os.environ, {
            'COPY_EXECUTION_MODE': 'LIVE',
            'ENABLE_LEVERAGE_LIMITS': 'true',
            'MAX_LEVERAGE': '500',
            'MAX_COPY_LEVERAGE': '100'
        }):
            flags_obj = FeatureFlags()
            assert flags_obj.get_max_leverage() == 100
        
        # Leverage limits disabled
        with patch.dict(os.environ, {
            'COPY_EXECUTION_MODE': 'LIVE',
            'ENABLE_LEVERAGE_LIMITS': 'false',
            'MAX_LEVERAGE': '500'
        }):
            flags_obj = FeatureFlags()
            assert flags_obj.get_max_leverage() == 500
    
    def test_get_position_limits(self):
        """Test position size limits based on mode and flags"""
        # Dry mode with position limits
        with patch.dict(os.environ, {
            'COPY_EXECUTION_MODE': 'DRY',
            'ENABLE_POSITION_LIMITS': 'true',
            'MIN_POSITION_SIZE': '1',
            'MAX_POSITION_SIZE': '100000'
        }):
            flags_obj = FeatureFlags()
            min_size, max_size = flags_obj.get_position_limits()
            assert min_size == 1
            assert max_size == 1000  # Lower limit in dry mode
        
        # Live mode with position limits
        with patch.dict(os.environ, {
            'COPY_EXECUTION_MODE': 'LIVE',
            'ENABLE_POSITION_LIMITS': 'true',
            'MIN_POSITION_SIZE': '1',
            'MAX_POSITION_SIZE': '100000'
        }):
            flags_obj = FeatureFlags()
            min_size, max_size = flags_obj.get_position_limits()
            assert min_size == 1
            assert max_size == 100000
        
        # Position limits disabled
        with patch.dict(os.environ, {
            'COPY_EXECUTION_MODE': 'LIVE',
            'ENABLE_POSITION_LIMITS': 'false',
            'MAX_POSITION_SIZE': '100000'
        }):
            flags_obj = FeatureFlags()
            min_size, max_size = flags_obj.get_position_limits()
            assert min_size == 0
            assert max_size == 100000
    
    def test_get_all_flags(self):
        """Test getting all flags"""
        flags_obj = FeatureFlags()
        all_flags = flags_obj.get_all_flags()
        
        assert isinstance(all_flags, dict)
        assert 'execution_mode' in all_flags
        assert 'emergency_stop' in all_flags
        assert 'enable_copy_trading' in all_flags
    
    def test_set_flag(self):
        """Test setting a flag value"""
        flags_obj = FeatureFlags()
        
        # Set a custom flag
        flags_obj.set_flag('custom_flag', True)
        
        assert flags_obj.is_feature_enabled('custom_flag') is True
    
    def test_get_status_summary(self):
        """Test getting status summary"""
        with patch.dict(os.environ, {
            'COPY_EXECUTION_MODE': 'DRY',
            'EMERGENCY_STOP': 'false',
            'MAINTENANCE_MODE': 'false',
            'ENABLE_COPY_TRADING': 'true',
            'ENABLE_AI_ANALYSIS': 'true',
            'ENABLE_LEADERBOARD': 'true',
            'ENABLE_TELEGRAM_COMMANDS': 'true'
        }):
            flags_obj = FeatureFlags()
            summary = flags_obj.get_status_summary()
            
            assert 'Execution Mode: 🔍 DRY' in summary
            assert 'System Status: ✅ RUNNING' in summary
            assert 'Maintenance: ✅ OPERATIONAL' in summary
            assert 'Copy Trading: ✅ ENABLED' in summary
            assert 'AI Features: ✅ ENABLED' in summary
            assert 'Leaderboard: ✅ ENABLED' in summary
            assert 'Telegram Commands: ✅ ENABLED' in summary
    
    def test_global_flags_instance(self):
        """Test that global flags instance works"""
        # Test that flags is accessible
        assert hasattr(flags, 'execution_mode')
        assert hasattr(flags, 'is_dry_mode')
        assert hasattr(flags, 'is_live_mode')
        assert hasattr(flags, 'can_execute_trades')
        assert hasattr(flags, 'can_copy_trade')
        assert hasattr(flags, 'get_all_flags')
        assert hasattr(flags, 'get_status_summary')
