"""
Configuration Settings
Centralized configuration management for the Vanta Bot
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Configuration class for the Vanta Bot"""
    
    # Environment
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
    DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    # Base Chain
    BASE_RPC_URL = os.getenv('BASE_RPC_URL', 'https://mainnet.base.org')
    BASE_CHAIN_ID = int(os.getenv('BASE_CHAIN_ID', 8453))
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost/vanta_bot')
    
    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    # Security
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
    
    # Contracts
    AVANTIS_TRADING_CONTRACT = os.getenv('AVANTIS_TRADING_CONTRACT')
    AVANTIS_VAULT_CONTRACT = os.getenv('AVANTIS_VAULT_CONTRACT')
    USDC_CONTRACT = os.getenv('USDC_CONTRACT', '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913')
    
    # Trading Configuration
    MAX_LEVERAGE = int(os.getenv('MAX_LEVERAGE', 500))
    MIN_POSITION_SIZE = int(os.getenv('MIN_POSITION_SIZE', 1))  # USDC
    MAX_POSITION_SIZE = int(os.getenv('MAX_POSITION_SIZE', 100000))  # USDC
    
    # Copy Trading Limits
    LEADER_ACTIVE_HOURS = int(os.getenv('LEADER_ACTIVE_HOURS', 72))
    LEADER_MIN_TRADES_30D = int(os.getenv('LEADER_MIN_TRADES_30D', 300))
    LEADER_MIN_VOLUME_30D_USD = int(os.getenv('LEADER_MIN_VOLUME_30D_USD', 10000000))
    MAX_COPY_SLIPPAGE_BPS = int(os.getenv('MAX_COPY_SLIPPAGE_BPS', 200))
    MAX_COPY_LEVERAGE = int(os.getenv('MAX_COPY_LEVERAGE', 100))
    MAX_COPYTRADERS_PER_USER = int(os.getenv('MAX_COPYTRADERS_PER_USER', 5))
    MAX_FOLLOWS_PER_COPYTRADER = int(os.getenv('MAX_FOLLOWS_PER_COPYTRADER', 10))
    
    # Performance Tuning
    AI_MODEL_UPDATE_INTERVAL = int(os.getenv('AI_MODEL_UPDATE_INTERVAL', 3600))  # 1 hour
    LEADERBOARD_CACHE_TTL = int(os.getenv('LEADERBOARD_CACHE_TTL', 300))      # 5 minutes
    POSITION_TRACKER_INTERVAL = int(os.getenv('POSITION_TRACKER_INTERVAL', 60))   # 1 minute
    EVENT_INDEXER_BATCH_SIZE = int(os.getenv('EVENT_INDEXER_BATCH_SIZE', 1000))
    
    # Rate Limiting
    COPY_EXECUTION_RATE_LIMIT = int(os.getenv('COPY_EXECUTION_RATE_LIMIT', 10))   # per minute
    TELEGRAM_MESSAGE_RATE_LIMIT = int(os.getenv('TELEGRAM_MESSAGE_RATE_LIMIT', 30)) # per minute per user
    
    # Monitoring
    ENABLE_METRICS = os.getenv('ENABLE_METRICS', 'true').lower() == 'true'
    SENTRY_DSN = os.getenv('SENTRY_DSN')
    
    # External APIs
    COINGECKO_API_KEY = os.getenv('COINGECKO_API_KEY')
    ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')
    
    # Email/SMTP (for alerts)
    SMTP_SERVER = os.getenv('SMTP_SERVER')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SMTP_USER = os.getenv('SMTP_USER')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')
    
    # Emergency Controls
    EMERGENCY_STOP_COPY_TRADING = os.getenv('EMERGENCY_STOP_COPY_TRADING', 'false').lower() == 'true'
    PAUSE_NEW_FOLLOWS = os.getenv('PAUSE_NEW_FOLLOWS', 'false').lower() == 'true'
    MAINTENANCE_MODE = os.getenv('MAINTENANCE_MODE', 'false').lower() == 'true'
    
    def validate(self) -> bool:
        """Validate required configuration values"""
        required_fields = [
            'TELEGRAM_BOT_TOKEN',
            'DATABASE_URL',
            'REDIS_URL', 
            'BASE_RPC_URL',
            'AVANTIS_TRADING_CONTRACT',
            'AVANTIS_VAULT_CONTRACT',
            'ENCRYPTION_KEY'
        ]
        
        missing_fields = []
        for field_name in required_fields:
            value = getattr(self, field_name)
            if not value or (isinstance(value, str) and value.strip() == ''):
                missing_fields.append(field_name)
        
        if missing_fields:
            raise ValueError(f"Missing required configuration fields: {', '.join(missing_fields)}")
        
        return True
    
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.ENVIRONMENT.lower() in ['production', 'prod']
    
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.ENVIRONMENT.lower() in ['development', 'dev', 'local']


# Global configuration instance
config = Config()
