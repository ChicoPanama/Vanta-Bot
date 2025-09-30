#!/usr/bin/env python3
"""
Analyze successful trades on BaseScan to find working parameters
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


async def analyze_successful_trades():
    print("🔍 ANALYZE SUCCESSFUL TRADES")
    print("=" * 60)
    print("⚠️  This will query recent successful trades to find working parameters")
    print("   And compare them to our bot parameters")
    print("=" * 60)

    try:
        # Connect to Base mainnet
        w3 = Web3(Web3.HTTPProvider("https://mainnet.base.org"))
        if not w3.is_connected():
            print("❌ Failed to connect to Base mainnet")
            return False

        print("✅ Connected to Base mainnet")

        # Avantis Trading contract address
        contract_address = "0x44914408af82bC9983bbb330e3578E1105e11d4e"

        # Get recent blocks to find transactions
        latest_block = w3.eth.block_number
        print(f"✅ Latest block: {latest_block}")

        # Look for recent transactions to this contract
        print(f"\n🔍 Searching for recent transactions to {contract_address}...")

        # Check last 100 blocks for transactions
        open_trade_transactions = []

        for block_num in range(latest_block - 100, latest_block + 1):
            try:
                block = w3.eth.get_block(block_num, full_transactions=True)

                for tx in block.transactions:
                    if tx.to and tx.to.lower() == contract_address.lower():
                        # Check if this is an openTrade transaction
                        if tx.input and len(tx.input) > 10:
                            # Look for openTrade function signature
                            if tx.input.startswith("0x"):  # Has input data
                                open_trade_transactions.append(
                                    {
                                        "hash": tx.hash.hex(),
                                        "block": block_num,
                                        "input": tx.input,
                                        "from": tx["from"],
                                        "value": tx.value,
                                    }
                                )

                                if (
                                    len(open_trade_transactions) >= 5
                                ):  # Get 5 recent ones
                                    break

                if len(open_trade_transactions) >= 5:
                    break

            except Exception as e:
                print(f"⚠️  Error checking block {block_num}: {e}")
                continue

        print(f"✅ Found {len(open_trade_transactions)} recent transactions")

        if not open_trade_transactions:
            print("❌ No recent transactions found")
            return False

        # Analyze each transaction
        for i, tx in enumerate(open_trade_transactions):
            print(f"\n📊 Transaction {i + 1}:")
            print(f"   Hash: {tx['hash']}")
            print(f"   Block: {tx['block']}")
            print(f"   From: {tx['from']}")
            print(f"   Value: {tx['value']} wei")
            print(f"   Input: {tx['input'][:100]}...")
            print(f"   BaseScan: https://basescan.org/tx/{tx['hash']}")

            # Try to decode the transaction input
            try:
                # Load the ABI to decode
                with open("config/abis/Trading.json") as f:
                    abi = json.load(f)

                contract = w3.eth.contract(address=contract_address, abi=abi)

                # Try to decode the function call
                try:
                    decoded = contract.decode_function_input(tx["input"])
                    print(f"   Function: {decoded[0].fn_name}")
                    print(f"   Parameters: {decoded[1]}")

                    # If it's openTrade, analyze the parameters
                    if decoded[0].fn_name == "openTrade":
                        params = decoded[1]
                        print("   ✅ This is an openTrade transaction!")
                        print(f"   Trade parameters: {params}")

                        # Extract key parameters
                        if "trade" in params:
                            trade_params = params["trade"]
                            print(f"   Trade struct: {trade_params}")

                        if "orderType" in params:
                            print(f"   Order type: {params['orderType']}")

                        if "slippageP" in params:
                            print(f"   Slippage: {params['slippageP']}")

                except Exception as decode_error:
                    print(f"   ⚠️  Could not decode transaction: {decode_error}")

            except Exception as e:
                print(f"   ⚠️  Error analyzing transaction: {e}")

        print("\n✅ ANALYSIS COMPLETE!")
        print("✅ Check the BaseScan links above to see successful trades")
        print("✅ Compare their parameters to our bot parameters")

        return True

    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(analyze_successful_trades())
    if success:
        print("\n🎉 ANALYSIS COMPLETED!")
        print("✅ Check the output for successful trade parameters")
    else:
        print("\n💥 ANALYSIS FAILED")
        print("❌ Check error details above")
        sys.exit(1)
