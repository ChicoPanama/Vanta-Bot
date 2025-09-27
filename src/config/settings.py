import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    # Base Chain
    BASE_RPC_URL = os.getenv('BASE_RPC_URL')
    BASE_CHAIN_ID = int(os.getenv('BASE_CHAIN_ID', 8453))
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    # Security
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
    
    # Contracts
    AVANTIS_TRADING_CONTRACT = os.getenv('AVANTIS_TRADING_CONTRACT')
    AVANTIS_VAULT_CONTRACT = os.getenv('AVANTIS_VAULT_CONTRACT')
    USDC_CONTRACT = os.getenv('USDC_CONTRACT')
    
    # Trading
    MAX_LEVERAGE = 500
    MIN_POSITION_SIZE = 1  # USDC
    MAX_POSITION_SIZE = 100000  # USDC
    
    # Bot Settings
    DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

config = Config()
