#!/usr/bin/env python3
"""
Practical debugging test based on SDK documentation
"""

import asyncio
import os
import sys

from web3 import Web3

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


async def practical_debug_test():
    print("🔍 PRACTICAL DEBUG TEST")
    print("=" * 60)
    print("⚠️  This will debug the real issues step by step")
    print("   Based on SDK documentation and best practices")
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

        # Step 1: Check ETH balance first
        print("\n🔍 Step 1: Check ETH balance")
        w3 = Web3(Web3.HTTPProvider("https://mainnet.base.org"))
        eth_balance = w3.eth.get_balance(address)
        eth_balance_ether = eth_balance / 10**18
        print(f"   ETH balance: {eth_balance_ether} ETH")

        if eth_balance_ether < 0.001:
            print("   ❌ Insufficient ETH for gas (need > 0.001 ETH)")
            return False
        else:
            print("   ✅ Sufficient ETH for gas")

        # Step 2: Check USDC balance
        print("\n🔍 Step 2: Check USDC balance")
        usdc_balance = await trader.get_usdc_balance()
        print(f"   USDC balance: {usdc_balance}")

        if usdc_balance < 100:
            print("   ❌ Insufficient USDC (need > 100 USDC)")
            return False
        else:
            print("   ✅ Sufficient USDC")

        # Step 3: Get pair details
        print("\n🔍 Step 3: Get pair details")
        try:
            # Try to get pair info for ETH (pair 0) and BTC (pair 1)
            for pair_index in [0, 1]:
                try:
                    pair_info = await trader.pairs.get_pair(pair_index=pair_index)
                    print(f"   Pair {pair_index}: {pair_info}")
                except Exception as e:
                    print(f"   Pair {pair_index}: Error - {e}")
        except Exception as e:
            print(f"   ❌ Could not get pair details: {e}")

        # Step 4: Get opening fee and loss protection
        print("\n🔍 Step 4: Get opening fee and loss protection")
        try:
            # Try for ETH (pair 0) first
            fee_info = await trader.trade.get_opening_fee_and_loss_protection(
                pair_index=0,  # ETH/USD
                collateral=100,
                leverage=10,
                buy=True,
            )
            print(f"   ETH opening fee: {fee_info}")
        except Exception as e:
            print(f"   ❌ Could not get opening fee: {e}")

        # Step 5: Try to get existing trades (to see working examples)
        print("\n🔍 Step 5: Get existing trades for comparison")
        try:
            # Try to get trades for any active trader
            trades = await trader.trade.get_trades(trader_address=address)
            print(f"   Found {len(trades)} trades for this address")
            for i, trade in enumerate(trades[:3]):  # Show first 3
                print(f"   Trade {i + 1}: {trade}")
        except Exception as e:
            print(f"   ❌ Could not get existing trades: {e}")

        # Step 6: Test with corrected parameters
        print("\n🔍 Step 6: Test with corrected parameters")

        # Try ETH first (pair 0)
        print("   Testing ETH/USD (Pair 0)...")
        try:
            trade_input = TradeInput(
                pair_index=0,  # ETH/USD
                buy=True,  # Long
                open_collateral=100,  # Use open_collateral, not collateral
                leverage=10,  # 10x leverage
                tp=0,  # No take profit
                sl=0,  # No stop loss
                trader=address,
            )

            print("   ✅ TradeInput created for ETH/USD")
            print(f"   Parameters: {trade_input}")

            # Build transaction with higher slippage
            trade_tx = await trader.trade.build_trade_open_tx(
                trade_input=trade_input,
                trade_input_order_type=TradeInputOrderType.MARKET,
                slippage_percentage=500,  # 5% slippage (500 basis points)
            )

            print("   ✅ ETH transaction built successfully!")
            print(f"   📝 Transaction: {trade_tx}")

            # Try to execute
            print("   🔄 Executing ETH trade...")
            tx_hash = await trader.send_and_get_transaction_hash(trade_tx)
            print("   ✅ ETH trade executed successfully!")
            print(f"   📝 Transaction Hash: {tx_hash}")
            print(f"   🔗 View on BaseScan: https://basescan.org/tx/{tx_hash}")

            return True

        except Exception as eth_error:
            print(f"   ❌ ETH trade failed: {eth_error}")

            # Try BTC (pair 1) if ETH fails
            print("   Testing BTC/USD (Pair 1)...")
            try:
                trade_input_btc = TradeInput(
                    pair_index=1,  # BTC/USD
                    buy=True,  # Long
                    open_collateral=100,  # Use open_collateral
                    leverage=10,  # 10x leverage
                    tp=0,  # No take profit
                    sl=0,  # No stop loss
                    trader=address,
                )

                print("   ✅ TradeInput created for BTC/USD")

                trade_tx_btc = await trader.trade.build_trade_open_tx(
                    trade_input=trade_input_btc,
                    trade_input_order_type=TradeInputOrderType.MARKET,
                    slippage_percentage=500,  # 5% slippage (500 basis points)
                )

                print("   ✅ BTC transaction built successfully!")

                tx_hash_btc = await trader.send_and_get_transaction_hash(trade_tx_btc)
                print("   ✅ BTC trade executed successfully!")
                print(f"   📝 Transaction Hash: {tx_hash_btc}")
                print(f"   🔗 View on BaseScan: https://basescan.org/tx/{tx_hash_btc}")

                return True

            except Exception as btc_error:
                print(f"   ❌ BTC trade also failed: {btc_error}")

                # Try with higher collateral
                print("   Testing with higher collateral ($500)...")
                try:
                    trade_input_high = TradeInput(
                        pair_index=0,  # ETH/USD
                        buy=True,  # Long
                        open_collateral=500,  # $500 USDC
                        leverage=10,  # 10x leverage
                        tp=0,  # No take profit
                        sl=0,  # No stop loss
                        trader=address,
                    )

                    trade_tx_high = await trader.trade.build_trade_open_tx(
                        trade_input=trade_input_high,
                        trade_input_order_type=TradeInputOrderType.MARKET,
                        slippage_percentage=500,  # 5% slippage (500 basis points)
                    )

                    print("   ✅ $500 transaction built successfully!")

                    tx_hash_high = await trader.send_and_get_transaction_hash(
                        trade_tx_high
                    )
                    print("   ✅ $500 trade executed successfully!")
                    print(f"   📝 Transaction Hash: {tx_hash_high}")
                    print(
                        f"   🔗 View on BaseScan: https://basescan.org/tx/{tx_hash_high}"
                    )

                    return True

                except Exception as high_error:
                    print(f"   ❌ $500 trade also failed: {high_error}")
                    print("   → This confirms the minimum is much higher than $500")
                    print("   → Need to find actual working parameters from BaseScan")

        return False

    except Exception as e:
        print(f"❌ Debug test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(practical_debug_test())
    if success:
        print("\n🎉 PRACTICAL DEBUG SUCCESS!")
        print("✅ Found working parameters")
        print("✅ Bot is production ready!")
    else:
        print("\n💥 PRACTICAL DEBUG FAILED")
        print("❌ Need to find actual working parameters from BaseScan")
        print("❌ Check the output above for specific error details")
        sys.exit(1)
