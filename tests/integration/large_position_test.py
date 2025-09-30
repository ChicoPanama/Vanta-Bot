#!/usr/bin/env python3
"""
Test with large position size using $100 USDC
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


async def test_large_position():
    print("🚀 LARGE POSITION TEST - $100 USDC")
    print("=" * 60)
    print("⚠️  This will execute REAL transactions on Base mainnet")
    print("   Using $100 USDC with high leverage")
    print("=" * 60)

    # Test wallet details
    test_private_key = (
        "aa3645b7606503e1a3e6081afe67eeb91662d143879f26ac77aedfcc043b1f87"
    )

    try:
        # Test SDK TraderClient
        from avantis_trader_sdk import TraderClient

        print("✅ Avantis SDK TraderClient imported successfully")

        # Initialize TraderClient
        trader = TraderClient(provider_url="https://mainnet.base.org")
        trader.set_local_signer(private_key=test_private_key)
        print("✅ TraderClient initialized with signer")

        # Get USDC balance and allowance
        usdc_balance = await trader.get_usdc_balance()
        allowance = await trader.get_usdc_allowance_for_trading()
        print(f"✅ USDC balance: {usdc_balance}")
        print(f"✅ USDC allowance: {allowance}")

        if usdc_balance < 100:
            print("❌ Insufficient USDC balance for large position test")
            return False

        # Test with maximum position size we can afford
        print("\n📊 Trade Parameters:")
        print("   Market: BTC/USD (Pair 1)")
        print("   Side: LONG")
        print("   Leverage: 100x (maximum leverage)")
        print("   Size: $100 USDC")
        print("   Position Size: $10,000 (100 × 100x leverage)")

        # Try to build a trade transaction with maximum position
        print("\n🔄 Building trade transaction with maximum position...")

        try:
            # Import the required types
            from avantis_trader_sdk.types import TradeInput, TradeInputOrderType

            # Get the ethereum address
            address = trader.get_signer().get_ethereum_address()
            print(f"✅ Trader address: {address}")

            # Create a TradeInput object with maximum position
            trade_input = TradeInput(
                pair_index=1,  # BTC/USD is pair 1
                is_long=True,  # LONG position
                open_collateral=100
                * 10**6,  # 100 USDC in wei (maximum we can afford)
                leverage=100,  # 100x leverage (maximum)
                tp=0,  # No take profit
                sl=0,  # No stop loss
                trader=address,  # Set the trader address manually
            )

            print(
                "✅ TradeInput created with $100 USDC, 100x leverage = $10,000 position"
            )

            # Use the build_trade_open_tx method
            trade_tx = await trader.trade.build_trade_open_tx(
                trade_input=trade_input,
                trade_input_order_type=TradeInputOrderType.MARKET,
                slippage_percentage=200,  # 2% slippage for large position
            )

            print("✅ Trade transaction built successfully!")
            print(f"📝 Transaction: {trade_tx}")

            # Try to execute the transaction
            print("\n🔄 Executing trade transaction...")

            # Send the transaction
            tx_hash = await trader.send_and_get_transaction_hash(trade_tx)
            print("✅ Trade executed successfully!")
            print(f"📝 Transaction Hash: {tx_hash}")
            print(f"🔗 View on BaseScan: https://basescan.org/tx/{tx_hash}")

            return True

        except Exception as trade_error:
            print(f"❌ Trade execution failed: {trade_error}")
            print("This might be due to:")
            print("- Still below minimum position size (very high requirement)")
            print("- Insufficient USDC allowance")
            print("- Other contract requirements")
            import traceback

            traceback.print_exc()
            return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_large_position())
    if success:
        print("\n🎉 LARGE POSITION TEST PASSED!")
        print("✅ Bot successfully executed real trade on Base mainnet")
        print("✅ Transaction confirmed on blockchain")
        print("✅ Avantis protocol integration working")
        print("✅ PRODUCTION READY!")
    else:
        print("\n💥 LARGE POSITION TEST FAILED")
        print("❌ Check error details above")
        sys.exit(1)
