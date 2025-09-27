"""
Configuration Settings
Centralized configuration management for the Vanta Bot
"""

import os
from typing import Optional, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Configuration class for the Vanta Bot"""
    
    def __init__(self):
        """Initialize configuration with environment variables"""
        # Environment
        self.ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
        self.DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        self.LOG_JSON = os.getenv('LOG_JSON', 'false').lower() == 'true'
        
        # Telegram
        self.TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
        
        # Base Chain
        self.BASE_RPC_URL = os.getenv('BASE_RPC_URL', 'https://mainnet.base.org')
        self.BASE_CHAIN_ID = int(os.getenv('BASE_CHAIN_ID', 8453))
        self.BASE_WS_URL = os.getenv('BASE_WS_URL', 'wss://mainnet.base.org')
        
        # Database
        self.DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///vanta_bot.db')
        
        # Redis
        self.REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
        
        # Security
        self.ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
        
        # Contracts
        self.AVANTIS_TRADING_CONTRACT = os.getenv('AVANTIS_TRADING_CONTRACT')
        self.AVANTIS_VAULT_CONTRACT = os.getenv('AVANTIS_VAULT_CONTRACT')
        self.USDC_CONTRACT = os.getenv('USDC_CONTRACT', '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913')
        
        # Avantis SDK Configuration
        self.TRADER_PRIVATE_KEY = os.getenv('TRADER_PRIVATE_KEY')
        self.AWS_KMS_KEY_ID = os.getenv('AWS_KMS_KEY_ID')
        self.AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
        self.PYTH_WS_URL = os.getenv('PYTH_WS_URL', 'wss://hermes.pyth.network/ws')
        
        # Copy Trading Configuration
        self.COPY_EXECUTION_MODE = os.getenv('COPY_EXECUTION_MODE', 'DRY')
        self.DEFAULT_SLIPPAGE_PCT = float(os.getenv('DEFAULT_SLIPPAGE_PCT', '1.0'))
        
        # Trading Configuration
        self.MAX_LEVERAGE = int(os.getenv('MAX_LEVERAGE', 500))
        self.MIN_POSITION_SIZE = int(os.getenv('MIN_POSITION_SIZE', 1))  # USDC
        self.MAX_POSITION_SIZE = int(os.getenv('MAX_POSITION_SIZE', 100000))  # USDC
        
        # Copy Trading Limits
        self.LEADER_ACTIVE_HOURS = int(os.getenv('LEADER_ACTIVE_HOURS', 72))
        self.LEADER_MIN_TRADES_30D = int(os.getenv('LEADER_MIN_TRADES_30D', 300))
        self.LEADER_MIN_VOLUME_30D_USD = int(os.getenv('LEADER_MIN_VOLUME_30D_USD', 10000000))
        self.MAX_COPY_SLIPPAGE_BPS = int(os.getenv('MAX_COPY_SLIPPAGE_BPS', 200))
        self.MAX_COPY_LEVERAGE = int(os.getenv('MAX_COPY_LEVERAGE', 100))
        self.MAX_COPYTRADERS_PER_USER = int(os.getenv('MAX_COPYTRADERS_PER_USER', 5))
        self.MAX_FOLLOWS_PER_COPYTRADER = int(os.getenv('MAX_FOLLOWS_PER_COPYTRADER', 10))
        
        # Indexer Configuration
        self.INDEXER_BACKFILL_RANGE = int(os.getenv('INDEXER_BACKFILL_RANGE', 50000))
        self.INDEXER_PAGE = int(os.getenv('INDEXER_PAGE', 2000))
        self.INDEXER_SLEEP_WS = int(os.getenv('INDEXER_SLEEP_WS', 2))
        self.INDEXER_SLEEP_HTTP = int(os.getenv('INDEXER_SLEEP_HTTP', 5))
        self.EVENT_BACKFILL_BLOCKS = int(os.getenv('EVENT_BACKFILL_BLOCKS', 1000))
        self.EVENT_MONITORING_INTERVAL = int(os.getenv('EVENT_MONITORING_INTERVAL', 5))
        
        # Performance Tuning
        self.AI_MODEL_UPDATE_INTERVAL = int(os.getenv('AI_MODEL_UPDATE_INTERVAL', 3600))  # 1 hour
        self.LEADERBOARD_CACHE_TTL = int(os.getenv('LEADERBOARD_CACHE_TTL', 300))      # 5 minutes
        self.POSITION_TRACKER_INTERVAL = int(os.getenv('POSITION_TRACKER_INTERVAL', 60))   # 1 minute
        self.EVENT_INDEXER_BATCH_SIZE = int(os.getenv('EVENT_INDEXER_BATCH_SIZE', 1000))
        
        # Rate Limiting
        self.COPY_EXECUTION_RATE_LIMIT = int(os.getenv('COPY_EXECUTION_RATE_LIMIT', 10))   # per minute
        self.TELEGRAM_MESSAGE_RATE_LIMIT = int(os.getenv('TELEGRAM_MESSAGE_RATE_LIMIT', 30)) # per minute per user
        
        # Monitoring
        self.ENABLE_METRICS = os.getenv('ENABLE_METRICS', 'true').lower() == 'true'
        self.SENTRY_DSN = os.getenv('SENTRY_DSN')
        
        # External APIs
        self.COINGECKO_API_KEY = os.getenv('COINGECKO_API_KEY')
        self.ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')
        
        # Email/SMTP (for alerts)
        self.SMTP_SERVER = os.getenv('SMTP_SERVER')
        self.SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
        self.SMTP_USER = os.getenv('SMTP_USER')
        self.SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
        self.ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')
        
        # Admin Controls
        self.ADMIN_USER_IDS = self._parse_admin_user_ids()
        self.SUPER_ADMIN_IDS = self._parse_super_admin_user_ids()
        
        # Emergency Controls
        self.EMERGENCY_STOP = os.getenv('EMERGENCY_STOP', 'false').lower() == 'true'
        self.EMERGENCY_STOP_COPY_TRADING = os.getenv('EMERGENCY_STOP_COPY_TRADING', 'false').lower() == 'true'
        self.PAUSE_NEW_FOLLOWS = os.getenv('PAUSE_NEW_FOLLOWS', 'false').lower() == 'true'
        self.MAINTENANCE_MODE = os.getenv('MAINTENANCE_MODE', 'false').lower() == 'true'
        
        # Risk Management
        self.MAX_POSITION_SIZE_USD = int(os.getenv('MAX_POSITION_SIZE_USD', '100000'))
        self.MAX_ACCOUNT_RISK_PCT = float(os.getenv('MAX_ACCOUNT_RISK_PCT', '0.10'))
        self.LIQUIDATION_BUFFER_PCT = float(os.getenv('LIQUIDATION_BUFFER_PCT', '0.05'))
        self.MAX_DAILY_LOSS_PCT = float(os.getenv('MAX_DAILY_LOSS_PCT', '0.20'))
        
        # Health Monitoring
        self.HEALTH_PORT = int(os.getenv('HEALTH_PORT', '8080'))
        
        # Risk Education (non-blocking)
        self.RISK_EDUCATION_ENABLED = os.getenv('RISK_EDUCATION_ENABLED', 'true').lower() == 'true'
        self.RISK_WARN_LEVERAGE_HIGH = float(os.getenv('RISK_WARN_LEVERAGE_HIGH', '50'))
        self.RISK_WARN_LEVERAGE_EXTREME = float(os.getenv('RISK_WARN_LEVERAGE_EXTREME', '200'))
        self.RISK_WARN_LIQUIDATION_PCT = float(os.getenv('RISK_WARN_LIQUIDATION_PCT', '0.01'))
        self.RISK_SCENARIO_STRESS_MOVE = float(os.getenv('RISK_SCENARIO_STRESS_MOVE', '0.02'))
        self.RISK_PROTOCOL_MAX_LEVERAGE = int(os.getenv('RISK_PROTOCOL_MAX_LEVERAGE', '500'))
        
        # Execution Mode
        self.DEFAULT_EXECUTION_MODE = os.getenv('DEFAULT_EXECUTION_MODE', 'DRY').upper()
    
    def _parse_admin_user_ids(self) -> List[int]:
        """Parse admin user IDs from environment variable"""
        admin_ids_str = os.getenv('ADMIN_USER_IDS', '')
        if not admin_ids_str:
            return []
        
        try:
            return [int(uid.strip()) for uid in admin_ids_str.split(',') if uid.strip()]
        except ValueError:
            return []
    
    def _parse_super_admin_user_ids(self) -> List[int]:
        """Parse super admin user IDs from environment variable"""
        admin_ids_str = os.getenv('SUPER_ADMIN_IDS', '')
        if not admin_ids_str:
            return []
        
        try:
            return [int(uid.strip()) for uid in admin_ids_str.split(',') if uid.strip()]
        except ValueError:
            return []
    
    def validate(self) -> bool:
        """Validate required configuration values by runtime mode"""
        # Core required fields for all modes
        core_required = [
            'TELEGRAM_BOT_TOKEN',
            'DATABASE_URL',
            'BASE_RPC_URL',
            'ENCRYPTION_KEY'
        ]
        
        # Bot mode requirements
        bot_required = core_required + ['REDIS_URL']
        
        # Indexer mode requirements  
        indexer_required = core_required + ['AVANTIS_TRADING_CONTRACT']
        
        # SDK mode requirements
        sdk_required = core_required + [
            'AVANTIS_TRADING_CONTRACT',
            'USDC_CONTRACT'
        ]
        
        # Determine mode based on environment or explicit setting
        mode = os.getenv('RUNTIME_MODE', 'BOT').upper()
        
        if mode == 'BOT':
            required_fields = bot_required
        elif mode == 'INDEXER':
            required_fields = indexer_required
        elif mode == 'SDK':
            required_fields = sdk_required
        else:
            required_fields = bot_required  # Default to bot mode
        
        missing_fields = []
        for field_name in required_fields:
            value = getattr(self, field_name)
            if not value or (isinstance(value, str) and value.strip() == ''):
                missing_fields.append(field_name)
        
        if missing_fields:
            raise ValueError(f"Missing required configuration fields for {mode} mode: {', '.join(missing_fields)}")
        
        return True
    
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.ENVIRONMENT.lower() in ['production', 'prod']
    
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.ENVIRONMENT.lower() in ['development', 'dev', 'local']
    
    def is_dry_mode(self) -> bool:
        """Check if running in dry mode (simulation)"""
        return self.COPY_EXECUTION_MODE.upper() == 'DRY'
    
    def is_live_mode(self) -> bool:
        """Check if running in live mode (real trading)"""
        return self.COPY_EXECUTION_MODE.upper() == 'LIVE'
    
    def runtime_summary(self) -> str:
        """Get runtime configuration summary for debugging (no secrets)"""
        return f"""
Configuration Summary:
- Environment: {self.ENVIRONMENT}
- Debug: {self.DEBUG}
- Log Level: {self.LOG_LEVEL}
- Log JSON: {self.LOG_JSON}
- Database: {self.DATABASE_URL.split('://')[0]}://...
- Redis: {self.REDIS_URL.split('://')[0]}://...
- Base RPC: {self.BASE_RPC_URL}
- Chain ID: {self.BASE_CHAIN_ID}
- Trading Contract: {self.AVANTIS_TRADING_CONTRACT[:10] + '...' if self.AVANTIS_TRADING_CONTRACT else 'Not set'}
- USDC Contract: {self.USDC_CONTRACT}
- Copy Mode: {self.COPY_EXECUTION_MODE}
- Emergency Stop: {self.EMERGENCY_STOP}
- Admin Users: {len(self.ADMIN_USER_IDS)} configured
- Indexer Backfill: {self.INDEXER_BACKFILL_RANGE} blocks
- Leader Min Trades: {self.LEADER_MIN_TRADES_30D}
- Leader Min Volume: ${self.LEADER_MIN_VOLUME_30D_USD:,}
        """.strip()


# Global configuration instance
settings = Config()
