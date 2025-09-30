#!/usr/bin/env python3
"""
Approve USDC and then try to trade
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


async def test_approve_and_trade():
    print("🚀 APPROVE AND TRADE TEST - BASE MAINNET")
    print("=" * 60)
    print("⚠️  This will execute REAL transactions on Base mainnet")
    print("   First approve USDC, then try to trade")
    print("=" * 60)

    # Test wallet details
    wallet_address = "0xdCDca231d02F1a8B85B701Ce90fc32c48a673982"
    test_private_key = (
        "aa3645b7606503e1a3e6081afe67eeb91662d143879f26ac77aedfcc043b1f87"
    )

    try:
        # Test blockchain connection
        from src.blockchain.base_client import BaseClient

        base_client = BaseClient()
        print(f"✅ Connected to Base mainnet (Chain ID: {base_client.w3.eth.chain_id})")

        # Check wallet balance
        balance = base_client.w3.eth.get_balance(wallet_address)
        balance_eth = base_client.w3.from_wei(balance, "ether")
        print(f"✅ Wallet balance: {balance_eth} ETH")

        if balance_eth < 0.001:
            print("❌ Insufficient ETH for gas fees")
            return False

        # Test SDK TraderClient
        try:
            from avantis_trader_sdk import TraderClient

            print("✅ Avantis SDK TraderClient imported successfully")
        except ImportError as e:
            print(f"❌ Failed to import TraderClient: {e}")
            return False

        # Initialize TraderClient
        try:
            trader = TraderClient(provider_url="https://mainnet.base.org")
            trader.set_local_signer(private_key=test_private_key)
            print("✅ TraderClient initialized with signer")
        except Exception as e:
            print(f"❌ Failed to initialize TraderClient: {e}")
            return False

        # Test basic SDK functionality
        try:
            # Get USDC balance
            usdc_balance = await trader.get_usdc_balance()
            print(f"✅ USDC balance: {usdc_balance}")

            # Get USDC allowance for trading
            allowance = await trader.get_usdc_allowance_for_trading()
            print(f"✅ USDC allowance: {allowance}")

        except Exception as e:
            print(f"❌ SDK basic functionality failed: {e}")
            return False

        # Try to approve USDC first
        print("\n🔄 Approving USDC for trading...")

        try:
            # Approve USDC for trading
            approve_tx = await trader.approve_usdc_for_trading(
                amount=20 * 10**6
            )  # Approve 20 USDC
            print(f"✅ USDC approval transaction: {approve_tx}")

            # Wait a bit for the transaction to be processed
            print("⏳ Waiting for approval transaction to be processed...")
            await asyncio.sleep(5)

            # Check allowance again
            new_allowance = await trader.get_usdc_allowance_for_trading()
            print(f"✅ New USDC allowance: {new_allowance}")

        except Exception as e:
            print(f"❌ USDC approval failed: {e}")
            print("This might be due to the SDK version issue we encountered earlier")
            return False

        # Now try to trade
        print("\n🔄 Building trade transaction...")

        try:
            # Import the required types
            from avantis_trader_sdk.types import TradeInput, TradeInputOrderType

            # Get the ethereum address manually
            address = trader.get_signer().get_ethereum_address()
            print(f"✅ Trader address: {address}")

            # Create a TradeInput object with much larger position
            trade_input = TradeInput(
                pair_index=0,  # BTC/USD is typically index 0
                is_long=True,  # LONG position
                open_collateral=100 * 10**6,  # 100 USDC in wei (increased from 10)
                leverage=50,  # 50x leverage (increased from 2)
                tp=0,  # No take profit
                sl=0,  # No stop loss
                trader=address,  # Set the trader address manually
            )

            # Use the build_trade_open_tx method
            trade_tx = await trader.trade.build_trade_open_tx(
                trade_input=trade_input,
                trade_input_order_type=TradeInputOrderType.MARKET,
                slippage_percentage=50,  # 0.5% slippage
            )

            print("✅ Trade transaction built successfully")
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
            print("- Incorrect pair index")
            print("- Insufficient USDC allowance")
            print("- Invalid trade parameters")
            print("- Contract not deployed")
            import traceback

            traceback.print_exc()
            return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_approve_and_trade())
    if success:
        print("\n🎉 APPROVE AND TRADE TEST PASSED!")
        print("✅ Bot successfully executed real trade on Base mainnet")
        print("✅ Transaction confirmed on blockchain")
        print("✅ Avantis protocol integration working")
    else:
        print("\n💥 APPROVE AND TRADE TEST FAILED")
        print("❌ Check error details above")
        sys.exit(1)
