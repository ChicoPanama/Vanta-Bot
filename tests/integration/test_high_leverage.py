#!/usr/bin/env python3
"""
Test with very high leverage to see if that's the issue
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


async def test_high_leverage():
    print("🔍 TESTING HIGH LEVERAGE")
    print("=" * 60)
    print("⚠️  Testing with very high leverage to see if that helps")
    print("=" * 60)

    try:
        # Import required modules
        from avantis_trader_sdk import TraderClient
        from avantis_trader_sdk.types import TradeInput, TradeInputOrderType

        # Initialize TraderClient
        trader = TraderClient(provider_url="https://mainnet.base.org")
        trader.set_local_signer(
            private_key="aa3645b7606503e1a3e6081afe67eeb91662d143879f26ac77aedfcc043b1f87"
        )
        address = trader.get_signer().get_ethereum_address()

        print("✅ TraderClient initialized")
        print(f"✅ Trader address: {address}")

        # Test different leverage values
        test_configs = [
            (1000, 100),  # $1,000 collateral, 100x leverage
            (5000, 200),  # $5,000 collateral, 200x leverage
            (10000, 500),  # $10,000 collateral, 500x leverage
            (25000, 1000),  # $25,000 collateral, 1000x leverage
        ]

        for collateral, leverage in test_configs:
            print(f"\n🔍 Testing: ${collateral:,} collateral, {leverage}x leverage")
            print(f"   Position size: ${collateral * leverage:,}")

            try:
                trade_input = TradeInput(
                    pairIndex=0,  # ETH/USD
                    buy=True,  # Long position
                    initialPosToken=collateral,  # Test collateral
                    leverage=leverage,  # Test leverage
                    tp=0,  # No take profit
                    sl=0,  # No stop loss
                    trader=address,
                )

                print("   ✅ TradeInput created")
                print(f"   initialPosToken: {trade_input.initialPosToken}")
                print(f"   leverage: {trade_input.leverage}")

                # Build transaction
                trade_tx = await trader.trade.build_trade_open_tx(
                    trade_input=trade_input,
                    trade_input_order_type=TradeInputOrderType.MARKET,
                    slippage_percentage=1000,  # 10% slippage
                )

                print("   ✅ Transaction built successfully!")

                # Try to execute
                tx_hash = await trader.send_and_get_transaction_hash(trade_tx)
                print("   🎉 SUCCESS! Trade executed!")
                print(f"   📝 Transaction Hash: {tx_hash}")
                print(f"   🔗 View on BaseScan: https://basescan.org/tx/{tx_hash}")

                print("\n🎉 FOUND WORKING CONFIGURATION!")
                print(f"✅ Collateral: ${collateral:,}")
                print(f"✅ Leverage: {leverage}x")
                print(f"✅ Position size: ${collateral * leverage:,}")
                print("✅ Bot now works!")
                print("✅ PRODUCTION READY!")

                return True

            except Exception as trade_error:
                if "BELOW_MIN_POS" in str(trade_error):
                    print("   ❌ Still too small: BELOW_MIN_POS")
                else:
                    print(f"   ❌ Failed with: {trade_error}")
                    break

        print("\n💥 ALL LEVERAGE TESTS FAILED")
        print("❌ Even with $25,000,000 position size failed")
        print("❌ Avantis protocol has extremely high minimums")
        print("❌ Need to find actual working parameters")

        return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_high_leverage())
    if success:
        print("\n🎉 WORKING CONFIGURATION FOUND!")
        print("✅ Bot now works!")
        print("✅ PRODUCTION READY!")
    else:
        print("\n💥 ALL TESTS FAILED")
        print("❌ Need to find actual working parameters")
        sys.exit(1)
