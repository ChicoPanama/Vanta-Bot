#!/bin/bash
# =============================================================================
# PRODUCTION ENVIRONMENT SETUP SCRIPT
# Sets verified Chainlink addresses and production configuration
# =============================================================================

set -e

echo "🚀 Setting up production environment with verified Chainlink addresses..."

# ===========================================
# VERIFIED CHAINLINK ADDRESSES (Base Network)
# ===========================================

# Crypto majors
export CHAINLINK_BTC_USD_FEED=0x64c911996D3c6aC71f9b455B1E8E7266BcbD848F
export CHAINLINK_ETH_USD_FEED=0x71041dddad3595F9CEd3DcCFBe3D1F4b0a16Bb70
export CHAINLINK_SOL_USD_FEED=0x975043adBb80fc32276CbF9Bbcfd4A601a12462D

# Coinbase-wrapped assets (often listed)
export CHAINLINK_CBBTC_USD_FEED=0x07DA0E54543a844a80ABE69c8A12F22B3aA59f9D
export CHAINLINK_CBETH_USD_FEED=0xd7818272B9e248357d13057AAb0B417aF31E817d

# Base-native token with feed
export CHAINLINK_AERO_USD_FEED=0x4EC5970fC728C5f65ba413992CD5fF6FD70fcfF0

# FX & commodities (if you enable those markets)
export CHAINLINK_EUR_USD_FEED=0xc91D5C4e0C8DC21E9a29Aa03C172421f313b3F0F
export CHAINLINK_XAU_USD_FEED=0x5213eBB69743b85644dbB6E25cdF994aFBb8cF31

# Stable/pegged on Base
export CHAINLINK_EURC_USD_FEED=0xDAe398520e2B67cd3f27aeF9Cf14D93D927f8250

# ===========================================
# PRODUCTION CONFIGURATION
# ===========================================

# Environment
export ENVIRONMENT=production
export DEBUG=false
export LOG_LEVEL=INFO

# Execution mode (start in DRY for safety)
export COPY_EXECUTION_MODE=DRY
export EMERGENCY_STOP=false

# Database (use async for main app)
export DATABASE_URL=sqlite+aiosqlite:///vanta_bot.db
# For PostgreSQL: postgresql+asyncpg://user:pass@localhost:5432/vanta_bot

# Redis for execution mode persistence
export REDIS_URL=redis://localhost:6379/0

# Blockchain
export BASE_RPC_URL=https://mainnet.base.org
export BASE_WS_URL=wss://mainnet.base.org
export BASE_CHAIN_ID=8453

# Avantis contracts
export AVANTIS_TRADING_CONTRACT=0x5FF292d70bA9cD9e7CCb313782811b3D7120535f
export USDC_CONTRACT=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913

# Pyth price feed
export PYTH_WS_URL=wss://hermes.pyth.network/ws
export PYTH_HERMES_ENDPOINT=https://hermes.pyth.network/v2/updates/price/latest
export PYTH_HERMES_ENDPOINT=https://hermes.pyth.network/v2/updates/price/latest

# Oracle Configuration (safe defaults)
export ORACLE_MAX_DEVIATION_BPS=50
export ORACLE_MAX_AGE_S=30

# Chainlink Sanity Ranges (safe defaults)
export CHAINLINK_SANITY_BTC_MIN=10000
export CHAINLINK_SANITY_BTC_MAX=200000
export CHAINLINK_SANITY_ETH_MIN=100
export CHAINLINK_SANITY_ETH_MAX=20000
export CHAINLINK_SANITY_SOL_MIN=10
export CHAINLINK_SANITY_SOL_MAX=1000

# ===========================================
# VALIDATION
# ===========================================

echo "✅ Environment variables set:"
echo "  - CHAINLINK_BTC_USD_FEED: $CHAINLINK_BTC_USD_FEED"
echo "  - CHAINLINK_ETH_USD_FEED: $CHAINLINK_ETH_USD_FEED"
echo "  - CHAINLINK_SOL_USD_FEED: $CHAINLINK_SOL_USD_FEED"
echo "  - ENVIRONMENT: $ENVIRONMENT"
echo "  - COPY_EXECUTION_MODE: $COPY_EXECUTION_MODE"
echo "  - REDIS_URL: $REDIS_URL"
echo "  - PYTH_HERMES_ENDPOINT: $PYTH_HERMES_ENDPOINT"

echo ""
echo "🔍 Running Chainlink feed validation..."

# Test Chainlink feed validation
python3 -c "
import os
import sys
sys.path.append('src')

from web3 import Web3
from src.services.oracle_providers.chainlink import ChainlinkOracle

# Set up Web3
w3 = Web3(Web3.HTTPProvider(os.getenv('BASE_RPC_URL', 'https://mainnet.base.org')))

try:
    oracle = ChainlinkOracle(w3)
    print('✅ Chainlink feeds validated successfully')
    print(f'   Available feeds: {list(oracle.aggregators.keys())}')
except Exception as e:
    print(f'❌ Chainlink validation failed: {e}')
    sys.exit(1)
"

echo ""
echo "🎯 Production environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Set your TELEGRAM_BOT_TOKEN"
echo "2. Set your TRADER_PRIVATE_KEY or AWS_KMS_KEY_ID"
echo "3. Set your ADMIN_USER_IDS"
echo "4. Run: python main.py"
echo ""
echo "⚠️  IMPORTANT: Start in DRY mode, then switch to LIVE after validation"
