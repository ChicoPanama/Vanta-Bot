#!/usr/bin/env python3
"""
Check the actual structure of TradeInput
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


async def check_tradeinput_structure():
    print("🔍 CHECK TRADEINPUT STRUCTURE")
    print("=" * 60)
    print("⚠️  This will show the actual structure of TradeInput")
    print("   To understand what parameters are available")
    print("=" * 60)

    try:
        # Import TradeInput
        from avantis_trader_sdk.types import TradeInput

        print("✅ TradeInput imported successfully")

        # Check the structure
        print("\n📊 TRADEINPUT STRUCTURE:")
        print(f"   TradeInput fields: {TradeInput.__fields__}")
        print(f"   TradeInput annotations: {TradeInput.__annotations__}")

        # Try to create a TradeInput with correct parameters
        print("\n🔄 CREATING TRADEINPUT WITH CORRECT PARAMETERS:")

        # Get the ethereum address
        from avantis_trader_sdk import TraderClient

        trader = TraderClient(provider_url="https://mainnet.base.org")
        trader.set_local_signer(
            private_key="aa3645b7606503e1a3e6081afe67eeb91662d143879f26ac77aedfcc043b1f87"
        )
        address = trader.get_signer().get_ethereum_address()

        print(f"   Trader address: {address}")

        # Try different parameter combinations
        try:
            # Method 1: Try with pair_index
            trade_input = TradeInput(
                pair_index=1,  # BTC/USD
                is_long=True,
                open_collateral=100 * 10**6,  # 100 USDC in wei
                leverage=100,
                tp=0,
                sl=0,
                trader=address,
            )
            print("   ✅ Method 1 (pair_index) worked!")
            print(f"   TradeInput: {trade_input}")

        except Exception as e:
            print(f"   ❌ Method 1 failed: {e}")

            # Method 2: Try without pair_index
            try:
                trade_input = TradeInput(
                    is_long=True,
                    open_collateral=100 * 10**6,  # 100 USDC in wei
                    leverage=100,
                    tp=0,
                    sl=0,
                    trader=address,
                )
                print("   ✅ Method 2 (no pair_index) worked!")
                print(f"   TradeInput: {trade_input}")

            except Exception as e2:
                print(f"   ❌ Method 2 failed: {e2}")

                # Method 3: Try with minimal parameters
                try:
                    trade_input = TradeInput(
                        open_collateral=100 * 10**6,  # 100 USDC in wei
                        leverage=100,
                        trader=address,
                    )
                    print("   ✅ Method 3 (minimal) worked!")
                    print(f"   TradeInput: {trade_input}")

                except Exception as e3:
                    print(f"   ❌ Method 3 failed: {e3}")

                    # Method 4: Check what parameters are actually required
                    print("   🔍 Checking required parameters...")
                    print(f"   TradeInput.__fields__: {TradeInput.__fields__}")

                    # Try to create with just the required fields
                    required_fields = [
                        field
                        for field, info in TradeInput.__fields__.items()
                        if info.is_required()
                    ]
                    print(f"   Required fields: {required_fields}")

                    # Create with only required fields
                    trade_input = TradeInput(**dict.fromkeys(required_fields, 0))
                    print("   ✅ Method 4 (required only) worked!")
                    print(f"   TradeInput: {trade_input}")

        print("\n✅ STRUCTURE CHECK COMPLETE!")
        print("✅ Now we know the correct TradeInput structure")

        return True

    except Exception as e:
        print(f"❌ Structure check failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(check_tradeinput_structure())
    if success:
        print("\n🎉 STRUCTURE CHECK COMPLETED!")
        print("✅ Now we know how to create TradeInput correctly")
    else:
        print("\n💥 STRUCTURE CHECK FAILED")
        print("❌ Check error details above")
        sys.exit(1)
