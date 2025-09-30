#!/usr/bin/env python3
"""
Avantis SDK Sanity Check Script

This script verifies that the Avantis Trader SDK is properly configured and working.
Run this script to test your SDK setup before using the bot.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from avantis_trader_sdk import TraderClient
from avantis_trader_sdk.types import TradeInput

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def check_sdk_connection():
    """Check basic SDK connection and configuration"""
    logger.info("🔍 Checking Avantis SDK connection...")

    try:
        # Get RPC URL from environment
        rpc_url = os.getenv("BASE_RPC_URL", "https://mainnet.base.org")
        logger.info(f"Using RPC URL: {rpc_url}")

        # Initialize TraderClient
        client = TraderClient(rpc_url)
        logger.info("✅ TraderClient initialized successfully")

        # Check if signer is configured
        private_key = os.getenv("TRADER_PRIVATE_KEY")
        aws_kms_key_id = os.getenv("AWS_KMS_KEY_ID")
        aws_region = os.getenv("AWS_REGION")

        if private_key:
            logger.info("🔑 Configuring local signer...")
            # Remove 0x prefix if present
            if private_key.startswith("0x"):
                private_key = private_key[2:]

            client.set_local_signer(private_key)
            trader_address = "configured" if client.has_signer() else None
            logger.info(f"✅ Local signer configured: {trader_address}")

        elif aws_kms_key_id:
            logger.info("🔑 Configuring AWS KMS signer...")
            region = aws_region or "us-east-1"
            client.set_aws_kms_signer(aws_kms_key_id, region)
            trader_address = "configured" if client.has_signer() else None
            logger.info(f"✅ AWS KMS signer configured: {trader_address}")

        else:
            logger.warning(
                "⚠️ No trader signer configured - trading operations will not work"
            )
            trader_address = None

        return client, trader_address

    except Exception as e:
        logger.error(f"❌ Failed to initialize TraderClient: {e}")
        return None, None


async def check_pairs_cache(client):
    """Check pairs cache functionality"""
    logger.info("🔍 Checking pairs cache...")

    try:
        # Get pairs count
        pairs_count = await client.pairs_cache.get_pairs_count()
        logger.info(f"✅ Found {pairs_count} trading pairs")

        # Try to get ETH/USD pair index
        try:
            eth_usd_index = await client.pairs_cache.get_pair_index("ETH/USD")
            logger.info(f"✅ ETH/USD pair index: {eth_usd_index}")
        except Exception as e:
            logger.warning(f"⚠️ Could not get ETH/USD pair index: {e}")

        # Try to get BTC/USD pair index
        try:
            btc_usd_index = await client.pairs_cache.get_pair_index("BTC/USD")
            logger.info(f"✅ BTC/USD pair index: {btc_usd_index}")
        except Exception as e:
            logger.warning(f"⚠️ Could not get BTC/USD pair index: {e}")

        return True

    except Exception as e:
        logger.error(f"❌ Error checking pairs cache: {e}")
        return False


async def check_trade_parameters(client, trader_address):
    """Check trade parameters and fee calculations"""
    logger.info("🔍 Checking trade parameters...")

    try:
        # Create a dummy trade input for ETH/USD
        trade_input = TradeInput(
            trader=trader_address or "0x0000000000000000000000000000000000000000",
            pair_index=0,  # Will be updated
            trade_index=0,
            open_collateral=100000000,  # $100 collateral (in 6 decimals)
            collateral_in_trade=100000000,  # $100 collateral (in 6 decimals)
            open_price=0,  # Market order
            is_long=True,  # Long position
            leverage=10000000,  # 10x leverage (in 6 decimals)
            tp=0,
            sl=0,
            timestamp=0,
        )

        # Try to get ETH/USD pair index first
        try:
            eth_usd_index = await client.pairs_cache.get_pair_index("ETH/USD")
            # Update the trade input with the correct pair index
            trade_data = trade_input.model_dump()
            trade_data["pair_index"] = eth_usd_index
            trade_input = TradeInput(**trade_data)
            logger.info(f"Using ETH/USD pair index: {eth_usd_index}")
        except Exception as e:
            logger.warning(f"⚠️ Could not get ETH/USD pair index, using 0: {e}")
            # Keep the default pair_index of 0

        # Get opening fee
        try:
            opening_fee = await client.fee_parameters.get_opening_fee(trade_input)
            logger.info(
                f"✅ Opening fee for $100 ETH/USD long @ 10x: {opening_fee} USDC"
            )
        except Exception as e:
            logger.warning(f"⚠️ Could not get opening fee: {e}")

        # Get loss protection
        try:
            opening_fee_usdc = await client.fee_parameters.get_opening_fee(trade_input)
            loss_protection = (
                await client.trading_parameters.get_loss_protection_for_trade_input(
                    trade_input, opening_fee_usdc=opening_fee_usdc
                )
            )
            logger.info(
                f"✅ Loss protection: {loss_protection.loss_protection_percent}% "
                f"({loss_protection.loss_protection_amount} USDC)"
            )
        except Exception as e:
            logger.warning(f"⚠️ Could not get loss protection: {e}")

        return True

    except Exception as e:
        logger.error(f"❌ Error checking trade parameters: {e}")
        return False


async def check_asset_parameters(client):
    """Check asset parameters and spreads"""
    logger.info("🔍 Checking asset parameters...")

    try:
        # Try to get pair spread for ETH/USD
        try:
            pair_spread = await client.asset_parameters.get_pair_spread("ETH/USD")
            logger.info(
                f"✅ ETH/USD pair spread: bid={pair_spread.bid_price}, ask={pair_spread.ask_price}"
            )
        except Exception as e:
            logger.warning(f"⚠️ Could not get ETH/USD pair spread: {e}")

        # Try to get price impact spread
        try:
            price_impact = await client.asset_parameters.get_price_impact_spread(
                position_size=1000.0,  # $1000 position
                is_long=True,
                pair="ETH/USD",
            )
            logger.info(f"✅ ETH/USD price impact spread (long $1000): {price_impact}")
        except Exception as e:
            logger.warning(f"⚠️ Could not get price impact spread: {e}")

        # Try to get skew impact spread
        try:
            skew_impact = await client.asset_parameters.get_skew_impact_spread(
                position_size=1000.0,  # $1000 position
                is_long=True,
                pair="ETH/USD",
            )
            logger.info(f"✅ ETH/USD skew impact spread (long $1000): {skew_impact}")
        except Exception as e:
            logger.warning(f"⚠️ Could not get skew impact spread: {e}")

        return True

    except Exception as e:
        logger.error(f"❌ Error checking asset parameters: {e}")
        return False


async def check_trader_operations(client, trader_address):
    """Check trader-specific operations"""
    logger.info("🔍 Checking trader operations...")

    if not trader_address:
        logger.warning("⚠️ No trader address available - skipping trader operations")
        return True

    try:
        # Check USDC allowance
        try:
            allowance = await client.get_usdc_allowance_for_trading(trader_address)
            logger.info(f"✅ USDC allowance for trading: {allowance} USDC")
        except Exception as e:
            logger.warning(f"⚠️ Could not get USDC allowance: {e}")

        # Check USDC balance
        try:
            balance = await client.get_usdc_balance(trader_address)
            logger.info(f"✅ USDC balance: {balance} USDC")
        except Exception as e:
            logger.warning(f"⚠️ Could not get USDC balance: {e}")

        # Check trades
        try:
            trades, pending_orders = await client.trade.get_trades(trader_address)
            logger.info(
                f"✅ Found {len(trades)} active trades and {len(pending_orders)} pending orders"
            )
        except Exception as e:
            logger.warning(f"⚠️ Could not get trades: {e}")

        return True

    except Exception as e:
        logger.error(f"❌ Error checking trader operations: {e}")
        return False


async def main():
    """Main sanity check function"""
    logger.info("🚀 Starting Avantis SDK Sanity Check")
    logger.info("=" * 50)

    # Check environment variables
    logger.info("🔍 Checking environment configuration...")
    required_vars = ["BASE_RPC_URL"]
    optional_vars = [
        "TRADER_PRIVATE_KEY",
        "AWS_KMS_KEY_ID",
        "AWS_REGION",
        "PYTH_WS_URL",
    ]

    for var in required_vars:
        if os.getenv(var):
            logger.info(f"✅ {var}: {os.getenv(var)}")
        else:
            logger.warning(f"⚠️ {var}: Not set")

    for var in optional_vars:
        if os.getenv(var):
            logger.info(
                f"✅ {var}: {'Set' if var != 'TRADER_PRIVATE_KEY' else 'Set (hidden)'}"
            )
        else:
            logger.info(f"ℹ️ {var}: Not set (optional)")

    logger.info("")

    # Check SDK connection
    client, trader_address = await check_sdk_connection()
    if not client:
        logger.error("❌ SDK connection failed - aborting checks")
        sys.exit(1)

    logger.info("")

    # Run all checks
    checks = [
        ("Pairs Cache", check_pairs_cache(client)),
        ("Trade Parameters", check_trade_parameters(client, trader_address)),
        ("Asset Parameters", check_asset_parameters(client)),
        ("Trader Operations", check_trader_operations(client, trader_address)),
    ]

    results = []
    for check_name, check_coro in checks:
        logger.info(f"🔍 Running {check_name} check...")
        try:
            result = await check_coro
            results.append((check_name, result))
            logger.info(f"✅ {check_name} check: {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            logger.error(f"❌ {check_name} check failed with exception: {e}")
            results.append((check_name, False))
        logger.info("")

    # Summary
    logger.info("=" * 50)
    logger.info("📊 SANITY CHECK SUMMARY")
    logger.info("=" * 50)

    passed_checks = sum(1 for _, result in results if result)
    total_checks = len(results)

    for check_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{check_name}: {status}")

    logger.info("")
    logger.info(f"Overall: {passed_checks}/{total_checks} checks passed")

    if passed_checks == total_checks:
        logger.info("🎉 All checks passed! Your Avantis SDK setup is ready.")
        sys.exit(0)
    else:
        logger.warning("⚠️ Some checks failed. Please review the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv

    load_dotenv()

    # Run the sanity check
    asyncio.run(main())
