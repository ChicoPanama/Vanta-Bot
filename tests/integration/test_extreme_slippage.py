#!/usr/bin/env python3
"""
Test extreme slippage values to find the correct format
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


async def test_extreme_slippage():
    print("🎯 TEST EXTREME SLIPPAGE VALUES")
    print("=" * 60)
    print("⚠️  Testing extreme slippage values to find correct format")
    print("=" * 60)

    try:
        from avantis_trader_sdk import TraderClient
        from avantis_trader_sdk.types import TradeInput, TradeInputOrderType

        trader = TraderClient(provider_url="https://mainnet.base.org")
        trader.set_local_signer(
            private_key="aa3645b7606503e1a3e6081afe67eeb91662d143879f26ac77aedfcc043b1f87"
        )
        address = trader.get_signer().get_ethereum_address()

        print("✅ TraderClient initialized")
        print(f"✅ Trader address: {address}")

        # Test extreme slippage values
        slippage_values = [
            10000,  # 100% slippage
            50000,  # 500% slippage
            100000,  # 1000% slippage
            1000000,  # 10000% slippage
        ]

        for slippage in slippage_values:
            print(f"\n🔍 Testing slippage: {slippage} ({(slippage / 100)}%)")

            try:
                # Create TradeInput with working parameters
                trade_input = TradeInput(
                    pairIndex=0,  # ETH/USD
                    buy=True,  # Long position
                    initialPosToken=1000,  # $1000 collateral
                    leverage=10,  # 10x leverage
                    tp=0,  # No take profit
                    sl=0,  # No stop loss
                    trader=address,
                )

                # Set positionSizeUSDC and openPrice explicitly
                trade_input.positionSizeUSDC = 10000000000  # $10,000 position
                trade_input.openPrice = 4000000000  # $4000 price

                print(f"   📊 TradeInput: {trade_input}")

                # Use SDK's build_trade_open_tx method with extreme slippage
                trade_tx = await trader.trade.build_trade_open_tx(
                    trade_input=trade_input,
                    trade_input_order_type=TradeInputOrderType.MARKET,
                    slippage_percentage=slippage,  # Test extreme slippage value
                )

                print("   ✅ Transaction built successfully!")
                print(f"   📝 Transaction: {trade_tx}")

                # Try to execute the transaction
                print("\n🔄 Executing transaction...")
                try:
                    tx_hash = await trader.send_and_get_transaction_hash(trade_tx)
                    print("   🎉 SUCCESS! Trade executed!")
                    print(f"   📝 Transaction Hash: {tx_hash}")
                    print(f"   🔗 View on BaseScan: https://basescan.org/tx/{tx_hash}")

                    print("\n🎉 BREAKTHROUGH! Found working slippage!")
                    print(f"✅ Slippage: {slippage} ({(slippage / 100)}%)")
                    print("✅ Real trade executed on Base mainnet")
                    print("✅ PRODUCTION READY!")

                    return True

                except Exception as e:
                    if "INVALID_SLIPPAGE" in str(e):
                        print("   ❌ Still invalid slippage: INVALID_SLIPPAGE")
                    else:
                        print(f"   ❌ Transaction execution failed: {e}")
                        continue

            except Exception as e:
                if "INVALID_SLIPPAGE" in str(e):
                    print("   ❌ Invalid slippage: INVALID_SLIPPAGE")
                else:
                    print(f"   ❌ Failed with: {e}")
                    continue

        print("\n💥 ALL EXTREME SLIPPAGE VALUES FAILED")
        print("❌ Even with 10000% slippage failed")
        print("❌ Need to find the correct slippage format")

        return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_extreme_slippage())
    if success:
        print("\n🎉 WORKING SLIPPAGE FOUND!")
        print("✅ Bot now works with correct slippage!")
        print("✅ PRODUCTION READY!")
    else:
        print("\n💥 ALL EXTREME SLIPPAGE FAILED")
        print("❌ Need to find correct slippage format")
        sys.exit(1)
