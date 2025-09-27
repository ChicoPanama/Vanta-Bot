"""
Test configuration loader and validation
"""
import os
import pytest
from unittest.mock import patch

from src.config.settings import Config, settings
from src.utils.errors import ConfigError


class TestConfig:
    """Test configuration loading and validation"""
    
    def test_config_initialization(self):
        """Test that config initializes with default values"""
        config = Config()
        
        # Test default values
        assert config.ENVIRONMENT == 'development'
        assert config.DEBUG is False
        assert config.LOG_LEVEL == 'INFO'
        assert config.BASE_CHAIN_ID == 8453
        assert config.COPY_EXECUTION_MODE == 'DRY'
        assert config.DEFAULT_SLIPPAGE_PCT == 1.0
    
    def test_config_environment_loading(self):
        """Test that config loads from environment variables"""
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'production',
            'DEBUG': 'true',
            'LOG_LEVEL': 'DEBUG',
            'BASE_CHAIN_ID': '1',
            'COPY_EXECUTION_MODE': 'LIVE',
            'DEFAULT_SLIPPAGE_PCT': '2.5'
        }):
            config = Config()
            
            assert config.ENVIRONMENT == 'production'
            assert config.DEBUG is True
            assert config.LOG_LEVEL == 'DEBUG'
            assert config.BASE_CHAIN_ID == 1
            assert config.COPY_EXECUTION_MODE == 'LIVE'
            assert config.DEFAULT_SLIPPAGE_PCT == 2.5
    
    def test_admin_user_ids_parsing(self):
        """Test admin user IDs parsing"""
        with patch.dict(os.environ, {
            'ADMIN_USER_IDS': '123456789,987654321,555666777'
        }):
            config = Config()
            
            assert config.ADMIN_USER_IDS == [123456789, 987654321, 555666777]
    
    def test_admin_user_ids_empty(self):
        """Test admin user IDs with empty value"""
        with patch.dict(os.environ, {
            'ADMIN_USER_IDS': ''
        }):
            config = Config()
            
            assert config.ADMIN_USER_IDS == []
    
    def test_admin_user_ids_invalid(self):
        """Test admin user IDs with invalid value"""
        with patch.dict(os.environ, {
            'ADMIN_USER_IDS': '123,invalid,456'
        }):
            config = Config()
            
            # Should return empty list for invalid values
            assert config.ADMIN_USER_IDS == []
    
    def test_validation_bot_mode(self):
        """Test validation for bot mode"""
        with patch.dict(os.environ, {
            'RUNTIME_MODE': 'BOT',
            'TELEGRAM_BOT_TOKEN': 'test_token',
            'DATABASE_URL': 'sqlite:///test.db',
            'BASE_RPC_URL': 'https://test.com',
            'ENCRYPTION_KEY': 'test_key',
            'REDIS_URL': 'redis://localhost:6379'
        }):
            config = Config()
            assert config.validate() is True
    
    def test_validation_indexer_mode(self):
        """Test validation for indexer mode"""
        with patch.dict(os.environ, {
            'RUNTIME_MODE': 'INDEXER',
            'TELEGRAM_BOT_TOKEN': 'test_token',
            'DATABASE_URL': 'sqlite:///test.db',
            'BASE_RPC_URL': 'https://test.com',
            'ENCRYPTION_KEY': 'test_key',
            'AVANTIS_TRADING_CONTRACT': '0x123'
        }):
            config = Config()
            assert config.validate() is True
    
    def test_validation_sdk_mode(self):
        """Test validation for SDK mode"""
        with patch.dict(os.environ, {
            'RUNTIME_MODE': 'SDK',
            'TELEGRAM_BOT_TOKEN': 'test_token',
            'DATABASE_URL': 'sqlite:///test.db',
            'BASE_RPC_URL': 'https://test.com',
            'ENCRYPTION_KEY': 'test_key',
            'AVANTIS_TRADING_CONTRACT': '0x123',
            'USDC_CONTRACT': '0x456'
        }):
            config = Config()
            assert config.validate() is True
    
    def test_validation_missing_required_fields(self):
        """Test validation fails with missing required fields"""
        with patch.dict(os.environ, {
            'RUNTIME_MODE': 'BOT',
            'TELEGRAM_BOT_TOKEN': '',  # Empty required field
            'DATABASE_URL': 'sqlite:///test.db',
            'BASE_RPC_URL': 'https://test.com',
            'ENCRYPTION_KEY': 'test_key',
            'REDIS_URL': 'redis://localhost:6379'
        }):
            config = Config()
            with pytest.raises(ValueError, match="Missing required configuration fields"):
                config.validate()
    
    def test_is_production(self):
        """Test production environment detection"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
            config = Config()
            assert config.is_production() is True
        
        with patch.dict(os.environ, {'ENVIRONMENT': 'prod'}):
            config = Config()
            assert config.is_production() is True
        
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            config = Config()
            assert config.is_production() is False
    
    def test_is_development(self):
        """Test development environment detection"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            config = Config()
            assert config.is_development() is True
        
        with patch.dict(os.environ, {'ENVIRONMENT': 'dev'}):
            config = Config()
            assert config.is_development() is True
        
        with patch.dict(os.environ, {'ENVIRONMENT': 'local'}):
            config = Config()
            assert config.is_development() is True
        
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
            config = Config()
            assert config.is_development() is False
    
    def test_is_dry_mode(self):
        """Test dry mode detection"""
        with patch.dict(os.environ, {'COPY_EXECUTION_MODE': 'DRY'}):
            config = Config()
            assert config.is_dry_mode() is True
        
        with patch.dict(os.environ, {'COPY_EXECUTION_MODE': 'dry'}):
            config = Config()
            assert config.is_dry_mode() is True
        
        with patch.dict(os.environ, {'COPY_EXECUTION_MODE': 'LIVE'}):
            config = Config()
            assert config.is_dry_mode() is False
    
    def test_is_live_mode(self):
        """Test live mode detection"""
        with patch.dict(os.environ, {'COPY_EXECUTION_MODE': 'LIVE'}):
            config = Config()
            assert config.is_live_mode() is True
        
        with patch.dict(os.environ, {'COPY_EXECUTION_MODE': 'live'}):
            config = Config()
            assert config.is_live_mode() is True
        
        with patch.dict(os.environ, {'COPY_EXECUTION_MODE': 'DRY'}):
            config = Config()
            assert config.is_live_mode() is False
    
    def test_runtime_summary(self):
        """Test runtime summary generation"""
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'production',
            'DEBUG': 'false',
            'LOG_LEVEL': 'INFO',
            'DATABASE_URL': 'sqlite:///test.db',
            'REDIS_URL': 'redis://localhost:6379',
            'BASE_RPC_URL': 'https://test.com',
            'AVANTIS_TRADING_CONTRACT': '0x1234567890123456789012345678901234567890',
            'COPY_EXECUTION_MODE': 'DRY',
            'EMERGENCY_STOP': 'false',
            'LEADER_MIN_TRADES_30D': '100',
            'LEADER_MIN_VOLUME_30D_USD': '50000'
        }):
            config = Config()
            summary = config.runtime_summary()
            
            assert 'Environment: production' in summary
            assert 'Debug: False' in summary
            assert 'Log Level: INFO' in summary
            assert 'Database: sqlite://...' in summary
            assert 'Redis: redis://...' in summary
            assert 'Base RPC: https://test.com' in summary
            assert 'Trading Contract: 0x1234567890...' in summary
            assert 'Copy Mode: DRY' in summary
            assert 'Emergency Stop: False' in summary
            assert 'Leader Min Trades: 100' in summary
            assert 'Leader Min Volume: $50,000' in summary
    
    def test_global_settings_instance(self):
        """Test that global settings instance works"""
        # Test that settings is accessible
        assert hasattr(settings, 'ENVIRONMENT')
        assert hasattr(settings, 'DATABASE_URL')
        assert hasattr(settings, 'validate')
        assert hasattr(settings, 'is_production')
        assert hasattr(settings, 'is_development')
        assert hasattr(settings, 'is_dry_mode')
        assert hasattr(settings, 'is_live_mode')
        assert hasattr(settings, 'runtime_summary')
