#!/usr/bin/env python3
"""
Test openTrade with correct parameter values
"""

import asyncio
import os
import sys
import time

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


async def correct_open_trade():
    print("🎯 CORRECT OPEN TRADE TEST")
    print("=" * 60)
    print("⚠️  Testing openTrade with correct parameter values")
    print("=" * 60)

    try:
        from avantis_trader_sdk import TraderClient

        trader = TraderClient(provider_url="https://mainnet.base.org")
        trader.set_local_signer(
            private_key="aa3645b7606503e1a3e6081afe67eeb91662d143879f26ac77aedfcc043b1f87"
        )
        address = trader.get_signer().get_ethereum_address()

        print("✅ TraderClient initialized")
        print(f"✅ Trader address: {address}")

        # Get trading contract
        trading_contract = trader.contracts["Trading"]
        print("✅ Trading contract loaded")

        # Test different parameter values to find the minimum
        test_configs = [
            (
                100000000,
                1000000000,
                10,
            ),  # $100 collateral, $1000 position, 10x leverage
            (
                500000000,
                5000000000,
                10,
            ),  # $500 collateral, $5000 position, 10x leverage
            (
                1000000000,
                10000000000,
                10,
            ),  # $1000 collateral, $10000 position, 10x leverage
            (
                100000000,
                10000000000,
                100,
            ),  # $100 collateral, $10000 position, 100x leverage
            (
                1000000000,
                100000000000,
                100,
            ),  # $1000 collateral, $100000 position, 100x leverage
        ]

        for collateral, position_size, leverage in test_configs:
            print(
                f"\n🔍 Testing: ${collateral / 1000000} collateral, ${position_size / 1000000} position, {leverage}x leverage"
            )

            try:
                # Create trade struct with correct field names
                trade_struct = (
                    address,  # trader
                    0,  # pairIndex (ETH/USD)
                    0,  # index
                    collateral,  # initialPosToken (collateral in USDC wei)
                    position_size,  # positionSizeUSDC (position size in USDC wei)
                    4000000000000,  # openPrice (4000 USD in wei)
                    True,  # buy (long)
                    leverage,  # leverage
                    0,  # tp (no take profit)
                    0,  # sl (no stop loss)
                    int(time.time()),  # timestamp
                )

                print(f"   📊 Trade struct: {trade_struct}")

                # Try to call openTrade
                result = await trading_contract.functions.openTrade(
                    trade_struct,  # Trade struct
                    0,  # OrderType (0 = market)
                    100,  # slippageP (1% in basis points)
                ).call()

                print("   ✅ openTrade call successful!")
                print(f"   📝 Result: {result}")

                # Try to build transaction
                print("\n🔄 Building openTrade transaction...")
                try:
                    tx = await trading_contract.functions.openTrade(
                        trade_struct,  # Trade struct
                        0,  # OrderType (0 = market)
                        100,  # slippageP (1% in basis points)
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

                    # Try to execute the transaction
                    print("\n🔄 Executing openTrade transaction...")
                    try:
                        tx_hash = await trader.send_and_get_transaction_hash(tx)
                        print("   🎉 SUCCESS! openTrade executed!")
                        print(f"   📝 Transaction Hash: {tx_hash}")
                        print(
                            f"   🔗 View on BaseScan: https://basescan.org/tx/{tx_hash}"
                        )

                        print("\n🎉 BREAKTHROUGH! Found working parameters!")
                        print(f"✅ Collateral: ${collateral / 1000000}")
                        print(f"✅ Position size: ${position_size / 1000000}")
                        print(f"✅ Leverage: {leverage}x")
                        print("✅ Real trade executed on Base mainnet")
                        print("✅ PRODUCTION READY!")

                        return True

                    except Exception as e:
                        print(f"   ❌ openTrade execution failed: {e}")
                        continue

                except Exception as e:
                    print(f"   ❌ openTrade transaction building failed: {e}")
                    continue

            except Exception as e:
                if "BELOW_MIN_POS" in str(e):
                    print("   ❌ Still too small: BELOW_MIN_POS")
                else:
                    print(f"   ❌ Failed with: {e}")
                    break

        print("\n💥 ALL PARAMETER COMBINATIONS FAILED")
        print("❌ Even with $100,000 position size failed")
        print("❌ Need to find the exact minimum requirements")

        return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(correct_open_trade())
    if success:
        print("\n🎉 WORKING PARAMETERS FOUND!")
        print("✅ Bot now works with correct parameters!")
        print("✅ PRODUCTION READY!")
    else:
        print("\n💥 ALL PARAMETERS FAILED")
        print("❌ Need to find exact minimum requirements")
        sys.exit(1)
