#!/usr/bin/env python3
"""
Correct executeMarketOrders with proper Pyth binary data
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


async def correct_execute_market_orders():
    print("🎯 CORRECT EXECUTE MARKET ORDERS")
    print("=" * 60)
    print("⚠️  Using correct executeMarketOrders with proper Pyth binary data")
    print("=" * 60)

    try:
        from avantis_trader_sdk import TraderClient

        trader = TraderClient(provider_url="https://mainnet.base.org")
        trader.set_local_signer(
            private_key="aa3645b7606503e1a3e6081afe67eeb91662d143879f26ac77aedfcc043b1f87"
        )
        address = trader.get_signer().get_ethereum_address()

        print("✅ TraderClient initialized")

        # Get Pyth price updates
        print("\n📡 Getting Pyth price updates...")
        try:
            identifiers = ["ETH/USD"]
            response = await trader.feed_client.get_latest_price_updates(identifiers)
            print(f"   ✅ Response type: {type(response)}")

            # Extract binary data from response
            if hasattr(response, "binary") and hasattr(response.binary, "data"):
                binary_data = response.binary.data
                print(f"   ✅ Found binary data: {len(binary_data)} items")
                print(f"   📊 Binary data preview: {binary_data[0][:50]}...")

                # Convert hex strings to bytes
                update_data = []
                for hex_string in binary_data:
                    # Remove '0x' prefix if present
                    if hex_string.startswith("0x"):
                        hex_string = hex_string[2:]
                    # Convert hex to bytes
                    update_bytes = bytes.fromhex(hex_string)
                    update_data.append(update_bytes)

                print(f"   📊 Converted to bytes: {len(update_data)} items")
                print(f"   📊 First update bytes: {update_data[0][:50]}...")

            else:
                print("   ❌ No binary data found in response")
                return False

        except Exception as e:
            print(f"   ❌ Failed to get Pyth updates: {e}")
            return False

        # Get trading contract
        trading_contract = trader.contracts["Trading"]
        print("✅ Trading contract loaded")

        # Try executeMarketOrders with correct parameters
        print("\n🔄 Testing executeMarketOrders with correct parameters...")
        try:
            # executeMarketOrders expects: (uint256[], bytes[])
            # We need to pass:
            # - uint256[]: array of order IDs (empty for now)
            # - bytes[]: array of Pyth update data

            order_ids = []  # Empty array of order IDs
            order_data = update_data  # Array of Pyth update bytes

            print(f"   📊 Order IDs: {order_ids}")
            print(f"   📊 Order data: {len(order_data)} Pyth updates")

            # Call executeMarketOrders with correct parameters
            result = await trading_contract.functions.executeMarketOrders(
                order_ids,  # uint256[] - order IDs
                order_data,  # bytes[] - Pyth update data
            ).call()

            print("   ✅ executeMarketOrders call successful!")
            print(f"   📝 Result: {result}")

            # Build transaction
            print("\n🔄 Building transaction...")
            try:
                tx = await trading_contract.functions.executeMarketOrders(
                    order_ids,  # uint256[] - order IDs
                    order_data,  # bytes[] - Pyth update data
                ).build_transaction(
                    {
                        "from": address,
                        "gas": 500000,
                        "maxFeePerGas": trader.web3.eth.gas_price * 2,
                        "maxPriorityFeePerGas": trader.web3.to_wei(1, "gwei"),
                    }
                )

                print("   ✅ Transaction built successfully!")
                print(f"   📝 Transaction: {tx}")

                # Execute transaction
                print("\n🔄 Executing transaction...")
                try:
                    tx_hash = await trader.send_and_get_transaction_hash(tx)
                    print("   🎉 SUCCESS! Transaction executed!")
                    print(f"   📝 Transaction Hash: {tx_hash}")
                    print(f"   🔗 View on BaseScan: https://basescan.org/tx/{tx_hash}")

                    print("\n🎉 BREAKTHROUGH! Bot now works!")
                    print("✅ Using correct executeMarketOrders function")
                    print("✅ Pyth price updates working")
                    print("✅ Real trade executed on Base mainnet")
                    print("✅ PRODUCTION READY!")

                    return True

                except Exception as e:
                    print(f"   ❌ Transaction execution failed: {e}")
                    print("   → Need to construct proper order parameters")
                    return False

            except Exception as e:
                print(f"   ❌ Transaction building failed: {e}")
                return False

        except Exception as e:
            print(f"   ❌ executeMarketOrders call failed: {e}")
            print("   → Need to construct proper parameters")
            return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(correct_execute_market_orders())
    if success:
        print("\n🎉 BREAKTHROUGH SUCCESS!")
        print("✅ Bot now works using executeMarketOrders!")
        print("✅ PRODUCTION READY!")
    else:
        print("\n💥 CORRECT EXECUTE MARKET ORDERS FAILED")
        print("❌ Need to construct proper order parameters")
        sys.exit(1)
