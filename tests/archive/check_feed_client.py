#!/usr/bin/env python3
"""
Check what methods the feed client has for getting Pyth data
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


async def check_feed_client():
    print("🔍 CHECKING FEED CLIENT METHODS")
    print("=" * 60)
    print("⚠️  Looking for Pyth data methods")
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

        # Check feed client methods
        print("\n📋 AVAILABLE FEED CLIENT METHODS:")
        feed_methods = []
        for method in dir(trader.feed_client):
            if not method.startswith("_"):
                feed_methods.append(method)
                print(f"   - {method}")

        # Try different methods to get Pyth data
        print("\n🔍 TRYING DIFFERENT PYTH DATA METHODS:")

        # Try get_price_feeds
        if hasattr(trader.feed_client, "get_price_feeds"):
            print("\n🔄 Testing get_price_feeds...")
            try:
                price_feeds = await trader.feed_client.get_price_feeds()
                print(f"   ✅ get_price_feeds SUCCESS: {price_feeds}")
            except Exception as e:
                print(f"   ❌ get_price_feeds failed: {e}")

        # Try get_latest_price_feeds
        if hasattr(trader.feed_client, "get_latest_price_feeds"):
            print("\n🔄 Testing get_latest_price_feeds...")
            try:
                latest_feeds = await trader.feed_client.get_latest_price_feeds()
                print(f"   ✅ get_latest_price_feeds SUCCESS: {latest_feeds}")
            except Exception as e:
                print(f"   ❌ get_latest_price_feeds failed: {e}")

        # Try get_update_data
        if hasattr(trader.feed_client, "get_update_data"):
            print("\n🔄 Testing get_update_data...")
            try:
                update_data = await trader.feed_client.get_update_data()
                print(f"   ✅ get_update_data SUCCESS: {update_data}")
            except Exception as e:
                print(f"   ❌ get_update_data failed: {e}")

        # Try get_price_update_data
        if hasattr(trader.feed_client, "get_price_update_data"):
            print("\n🔄 Testing get_price_update_data...")
            try:
                price_update_data = await trader.feed_client.get_price_update_data()
                print(f"   ✅ get_price_update_data SUCCESS: {price_update_data}")
            except Exception as e:
                print(f"   ❌ get_price_update_data failed: {e}")

        # Try get_pyth_update_data
        if hasattr(trader.feed_client, "get_pyth_update_data"):
            print("\n🔄 Testing get_pyth_update_data...")
            try:
                pyth_update_data = await trader.feed_client.get_pyth_update_data()
                print(f"   ✅ get_pyth_update_data SUCCESS: {pyth_update_data}")
            except Exception as e:
                print(f"   ❌ get_pyth_update_data failed: {e}")

        # Try to get update data for specific pairs
        print("\n🔄 Testing with specific pair...")
        try:
            # Try to get update data for ETH/USD (pair 0)
            if hasattr(trader.feed_client, "get_update_data_for_pair"):
                update_data = await trader.feed_client.get_update_data_for_pair(0)
                print(f"   ✅ get_update_data_for_pair SUCCESS: {update_data}")
            else:
                print("   ❌ get_update_data_for_pair not found")
        except Exception as e:
            print(f"   ❌ get_update_data_for_pair failed: {e}")

        # Try to manually construct Pyth update data
        print("\n🔄 Trying to manually construct Pyth update data...")
        try:
            # Get current price for ETH/USD
            if hasattr(trader.feed_client, "get_price"):
                eth_price = await trader.feed_client.get_price("ETH/USD")
                print(f"   ✅ ETH price: {eth_price}")

                # Try to construct update data
                if hasattr(trader.feed_client, "construct_update_data"):
                    update_data = await trader.feed_client.construct_update_data(
                        [eth_price]
                    )
                    print(f"   ✅ Constructed update data: {update_data}")
                else:
                    print("   ❌ construct_update_data not found")
            else:
                print("   ❌ get_price not found")
        except Exception as e:
            print(f"   ❌ Manual construction failed: {e}")

        return False

    except Exception as e:
        print(f"❌ Check failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(check_feed_client())
    if success:
        print("\n🎉 PYTH DATA METHOD FOUND!")
        print("✅ Bot can now get Pyth update data!")
        print("✅ PRODUCTION READY!")
    else:
        print("\n💥 NO PYTH DATA METHODS FOUND")
        print("❌ Need to find the correct method for Pyth data")
        sys.exit(1)
