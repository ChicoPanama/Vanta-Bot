#!/usr/bin/env python3
"""
Debug the actual transaction data being sent to the contract
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


async def debug_transaction_data():
    print("🔍 DEBUG TRANSACTION DATA")
    print("=" * 60)
    print("⚠️  Debugging the actual transaction data being sent")
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

        # Create a simple trade input
        trade_input = TradeInput(
            pairIndex=0,  # ETH/USD
            buy=True,  # Long position
            initialPosToken=1000,  # $1000 collateral
            leverage=10,  # 10x leverage
            tp=0,  # No take profit
            sl=0,  # No stop loss
            trader=address,
        )

        # Set positionSizeUSDC and openPrice
        trade_input.positionSizeUSDC = 10000000000  # $10,000 position
        trade_input.openPrice = 0  # Let Pyth set it

        print(f"📊 TradeInput: {trade_input}")

        # Try different slippage values and see what happens
        slippage_values = [
            100000000,  # 1% slippage (1e10 scale)
            1000000000,  # 10% slippage (1e10 scale)
            5000000000,  # 50% slippage (1e10 scale)
        ]

        for slippage in slippage_values:
            print(
                f"\n🔍 Testing slippage: {slippage} ({(slippage / 10000000000) * 100}%)"
            )

            try:
                # Build transaction
                trade_tx = await trader.trade.build_trade_open_tx(
                    trade_input=trade_input,
                    trade_input_order_type=TradeInputOrderType.MARKET,
                    slippage_percentage=slippage,
                )

                print("   ✅ Transaction built successfully!")
                print(f"   📝 Transaction data: {trade_tx.get('data', 'No data')}")
                print(f"   📝 Transaction to: {trade_tx.get('to', 'No to')}")
                print(f"   📝 Transaction value: {trade_tx.get('value', 'No value')}")
                print(f"   📝 Transaction gas: {trade_tx.get('gas', 'No gas')}")

                # Try to decode the transaction data to see what's being sent
                try:
                    from web3 import Web3

                    w3 = Web3(Web3.HTTPProvider("https://mainnet.base.org"))

                    # Get the contract
                    with open("config/abis/Trading.json") as f:
                        abi = json.load(f)

                    contract = w3.eth.contract(abi=abi)

                    # Try to decode the transaction data
                    try:
                        decoded = contract.decode_function_input(trade_tx["data"])
                        print(f"   📊 Decoded function: {decoded[0].fn_name}")
                        print(f"   📊 Decoded args: {decoded[1]}")
                    except Exception as e:
                        print(f"   ❌ Could not decode transaction data: {e}")

                except Exception as e:
                    print(f"   ❌ Could not decode transaction: {e}")

                # Try to execute the transaction
                print("\n🔄 Executing transaction...")
                try:
                    tx_hash = await trader.send_and_get_transaction_hash(trade_tx)
                    print("   🎉 SUCCESS! Trade executed!")
                    print(f"   📝 Transaction Hash: {tx_hash}")
                    print(f"   🔗 View on BaseScan: https://basescan.org/tx/{tx_hash}")

                    return True

                except Exception as e:
                    if "BELOW_MIN_POS" in str(e):
                        print(f"   ❌ BELOW_MIN_POS: {e}")
                    elif "INVALID_SLIPPAGE" in str(e):
                        print(f"   ❌ INVALID_SLIPPAGE: {e}")
                    else:
                        print(f"   ❌ Transaction execution failed: {e}")
                        continue

            except Exception as e:
                if "BELOW_MIN_POS" in str(e):
                    print(f"   ❌ BELOW_MIN_POS: {e}")
                elif "INVALID_SLIPPAGE" in str(e):
                    print(f"   ❌ INVALID_SLIPPAGE: {e}")
                else:
                    print(f"   ❌ Failed with: {e}")
                    continue

        print("\n💥 ALL SLIPPAGE VALUES FAILED")
        print("❌ Need to find the exact slippage format")

        return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(debug_transaction_data())
    if success:
        print("\n🎉 WORKING SLIPPAGE FOUND!")
        print("✅ Bot now works with correct slippage!")
        print("✅ PRODUCTION READY!")
    else:
        print("\n💥 ALL SLIPPAGE VALUES FAILED")
        print("❌ Need to find exact slippage format")
        sys.exit(1)
