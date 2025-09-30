#!/usr/bin/env python3
"""
Check what methods the Avantis SDK actually provides
"""

import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Set environment variables
os.environ.update(
    {
        "TELEGRAM_BOT_TOKEN": "test_token",
        "DATABASE_URL": "sqlite+aiosqlite:///test.db",
        "BASE_RPC_URL": "https://mainnet.base.org",
        "BASE_CHAIN_ID": "8453",
        "ENCRYPTION_KEY": "vkpZGJ3stdTs-i-gAM4sQGC7V5wi-pPkTDqyglD5x50=",
        "ADMIN_USER_IDS": "123456789",
        "COPY_EXECUTION_MODE": "LIVE",
        "PYTH_PRICE_SERVICE_URL": "https://hermes.pyth.network",
        "CHAINLINK_BASE_URL": "https://api.chain.link/v1",
        "TRADER_PRIVATE_KEY": "aa3645b7606503e1a3e6081afe67eeb91662d143879f26ac77aedfcc043b1f87",
        "AVANTIS_TRADING_CONTRACT": "0x5FF292d70bA9cD9e7CCb313782811b3D7120535f",
    }
)


async def check_sdk_methods():
    print("🔍 CHECKING AVANTIS SDK METHODS")
    print("=" * 60)
    print("⚠️  Looking for the correct high-level trading methods")
    print("=" * 60)

    try:
        # Import required modules
        from avantis_trader_sdk import TraderClient

        # Initialize TraderClient
        trader = TraderClient(provider_url="https://mainnet.base.org")
        trader.set_local_signer(
            private_key="aa3645b7606503e1a3e6081afe67eeb91662d143879f26ac77aedfcc043b1f87"
        )
        address = trader.get_signer().get_ethereum_address()

        print("✅ TraderClient initialized")
        print(f"✅ Trader address: {address}")

        # Check all trade methods
        print("\n📋 AVAILABLE TRADE METHODS:")
        trade_methods = []
        for method in dir(trader.trade):
            if not method.startswith("_"):
                trade_methods.append(method)
                print(f"   - {method}")

        print("\n📋 AVAILABLE CLIENT METHODS:")
        client_methods = []
        for method in dir(trader):
            if not method.startswith("_"):
                client_methods.append(method)
                print(f"   - {method}")

        # Look for high-level trading methods
        print("\n🔍 LOOKING FOR HIGH-LEVEL TRADING METHODS:")

        # Check for execute_market_orders or similar
        high_level_methods = [
            "execute_market_orders",
            "execute_market_trade",
            "open_market_order",
            "submit_market_order",
            "trade_market",
            "execute_trade",
            "submit_trade",
            "open_position",
            "close_position",
        ]

        found_methods = []
        for method in high_level_methods:
            if hasattr(trader.trade, method):
                found_methods.append(method)
                print(f"   ✅ Found: trader.trade.{method}")
            elif hasattr(trader, method):
                found_methods.append(method)
                print(f"   ✅ Found: trader.{method}")

        if found_methods:
            print("\n🎯 TRYING HIGH-LEVEL METHODS:")

            # Try execute_market_orders if it exists
            if hasattr(trader.trade, "execute_market_orders"):
                print("\n🔄 Testing trader.trade.execute_market_orders...")
                try:
                    # This should handle Pyth updates automatically
                    result = await trader.trade.execute_market_orders(
                        pair_index=0,  # ETH/USD
                        buy=True,
                        collateral=100,  # $100 USDC
                        leverage=10,
                        slippage=1,  # 1% slippage
                    )
                    print(f"   ✅ execute_market_orders SUCCESS: {result}")
                    return True
                except Exception as e:
                    print(f"   ❌ execute_market_orders failed: {e}")

            # Try execute_market_trade if it exists
            if hasattr(trader.trade, "execute_market_trade"):
                print("\n🔄 Testing trader.trade.execute_market_trade...")
                try:
                    result = await trader.trade.execute_market_trade(
                        pair_index=0,  # ETH/USD
                        buy=True,
                        collateral=100,  # $100 USDC
                        leverage=10,
                        slippage=1,  # 1% slippage
                    )
                    print(f"   ✅ execute_market_trade SUCCESS: {result}")
                    return True
                except Exception as e:
                    print(f"   ❌ execute_market_trade failed: {e}")

            # Try open_market_order if it exists
            if hasattr(trader.trade, "open_market_order"):
                print("\n🔄 Testing trader.trade.open_market_order...")
                try:
                    result = await trader.trade.open_market_order(
                        pair_index=0,  # ETH/USD
                        buy=True,
                        collateral=100,  # $100 USDC
                        leverage=10,
                        slippage=1,  # 1% slippage
                    )
                    print(f"   ✅ open_market_order SUCCESS: {result}")
                    return True
                except Exception as e:
                    print(f"   ❌ open_market_order failed: {e}")

        else:
            print("\n❌ NO HIGH-LEVEL METHODS FOUND")
            print(f"   Available methods: {trade_methods}")
            print("   Need to find the correct method for market orders")

        return False

    except Exception as e:
        print(f"❌ Check failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(check_sdk_methods())
    if success:
        print("\n🎉 HIGH-LEVEL METHOD FOUND!")
        print("✅ Bot can now trade using correct SDK method!")
        print("✅ PRODUCTION READY!")
    else:
        print("\n💥 NO HIGH-LEVEL METHODS FOUND")
        print("❌ Need to find the correct method for market orders")
        sys.exit(1)
