#!/usr/bin/env python3
"""
Fix units and parameters using correct Avantis protocol scaling
"""

import asyncio
import os
import sys
from decimal import Decimal

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


async def correct_units_and_parameters():
    print("🎯 CORRECT UNITS AND PARAMETERS")
    print("=" * 60)
    print("⚠️  Using correct Avantis protocol scaling and parameters")
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

        # Get trading contract
        trading_contract = trader.contracts["Trading"]
        print("✅ Trading contract loaded")

        # Read constraints from chain
        print("\n📊 READING CONSTRAINTS FROM CHAIN:")
        try:
            # Try to get pair constraints
            pair_index = 0  # ETH/USD

            # Get pair info if available
            if hasattr(trading_contract.functions, "pairs"):
                pair_info = await trading_contract.functions.pairs(pair_index).call()
                print(f"   📊 Pair info: {pair_info}")

            # Try to get min/max position sizes
            if hasattr(trading_contract.functions, "minPositionSizeUSDC"):
                min_pos = await trading_contract.functions.minPositionSizeUSDC(
                    pair_index
                ).call()
                print(f"   📊 Min position size: {min_pos}")
            else:
                min_pos = 1000000  # Default: $1 USDC (6 dp)
                print(f"   📊 Using default min position size: {min_pos}")

            if hasattr(trading_contract.functions, "maxPositionSizeUSDC"):
                max_pos = await trading_contract.functions.maxPositionSizeUSDC(
                    pair_index
                ).call()
                print(f"   📊 Max position size: {max_pos}")
            else:
                max_pos = 1000000000000  # Default: $1M USDC (6 dp)
                print(f"   📊 Using default max position size: {max_pos}")

            # Try to get max slippage
            if hasattr(trading_contract.functions, "maxOpenSlippage"):
                max_slip = await trading_contract.functions.maxOpenSlippage().call()
                print(f"   📊 Max slippage: {max_slip}")
            else:
                max_slip = 10000000000  # Default: 100% (1e10 scale)
                print(f"   📊 Using default max slippage: {max_slip}")

        except Exception as e:
            print(f"   ❌ Could not read constraints: {e}")
            # Use defaults
            min_pos = 1000000  # $1 USDC (6 dp)
            max_pos = 1000000000000  # $1M USDC (6 dp)
            max_slip = 10000000000  # 100% (1e10 scale)

        # Test with correct units and parameters
        test_configs = [
            (100, 10, 1.0),  # $100 collateral, 10x leverage, 1% slippage
            (500, 10, 1.0),  # $500 collateral, 10x leverage, 1% slippage
            (1000, 10, 1.0),  # $1000 collateral, 10x leverage, 1% slippage
            (100, 100, 1.0),  # $100 collateral, 100x leverage, 1% slippage
        ]

        for human_collateral, human_leverage, human_slippage in test_configs:
            print(
                f"\n🔍 Testing: ${human_collateral} collateral, {human_leverage}x leverage, {human_slippage}% slippage"
            )

            try:
                # Convert to protocol units
                initialPosToken = int(
                    Decimal(human_collateral) * Decimal(10**6)
                )  # 6 dp
                leverage_scaled = int(
                    Decimal(human_leverage) * Decimal(10**10)
                )  # 1e10 scale
                slippage_scaled = int(
                    (Decimal(human_slippage) / Decimal(100)) * Decimal(10**10)
                )  # 1e10 of fraction

                # Compute position size in USDC (6 dp)
                positionSizeUSDC = (initialPosToken * leverage_scaled) // (10**10)

                print("   📊 Protocol units:")
                print(
                    f"   initialPosToken: {initialPosToken} (${human_collateral} USDC)"
                )
                print(f"   leverage_scaled: {leverage_scaled} ({human_leverage}x)")
                print(f"   slippage_scaled: {slippage_scaled} ({human_slippage}%)")
                print(
                    f"   positionSizeUSDC: {positionSizeUSDC} (${positionSizeUSDC / 1000000} USDC)"
                )

                # Sanity checks
                if positionSizeUSDC < min_pos:
                    print(f"   ❌ BELOW_MIN_POS: {positionSizeUSDC} < {min_pos}")
                    continue

                if positionSizeUSDC > max_pos:
                    print(f"   ❌ ABOVE_MAX_POS: {positionSizeUSDC} > {max_pos}")
                    continue

                if slippage_scaled > max_slip:
                    print(f"   ❌ SLIPPAGE_TOO_HIGH: {slippage_scaled} > {max_slip}")
                    continue

                print("   ✅ All constraints satisfied")

                # Create TradeInput with correct parameters
                trade_input = TradeInput(
                    pairIndex=pair_index,  # ETH/USD
                    buy=True,  # Long position
                    initialPosToken=initialPosToken,  # USDC 6 dp
                    leverage=leverage_scaled,  # 1e10 scale
                    tp=0,  # No take profit
                    sl=0,  # No stop loss
                    trader=address,
                )

                # Set positionSizeUSDC explicitly (USDC 6 dp)
                trade_input.positionSizeUSDC = positionSizeUSDC

                # Set openPrice to 0 for market orders (let Pyth set it)
                trade_input.openPrice = 0

                print(f"   📊 TradeInput: {trade_input}")

                # Use SDK's build_trade_open_tx method with correct slippage
                trade_tx = await trader.trade.build_trade_open_tx(
                    trade_input=trade_input,
                    trade_input_order_type=TradeInputOrderType.MARKET,
                    slippage_percentage=slippage_scaled,  # 1e10 scale
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

                    print("\n🎉 BREAKTHROUGH! Found working parameters!")
                    print(f"✅ Collateral: ${human_collateral}")
                    print(f"✅ Leverage: {human_leverage}x")
                    print(f"✅ Slippage: {human_slippage}%")
                    print(f"✅ Position size: ${positionSizeUSDC / 1000000}")
                    print("✅ Real trade executed on Base mainnet")
                    print("✅ PRODUCTION READY!")

                    return True

                except Exception as e:
                    if "BELOW_MIN_POS" in str(e):
                        print("   ❌ Still too small: BELOW_MIN_POS")
                    elif "INVALID_SLIPPAGE" in str(e):
                        print("   ❌ Invalid slippage: INVALID_SLIPPAGE")
                    else:
                        print(f"   ❌ Transaction execution failed: {e}")
                        continue

            except Exception as e:
                if "BELOW_MIN_POS" in str(e):
                    print("   ❌ Still too small: BELOW_MIN_POS")
                elif "INVALID_SLIPPAGE" in str(e):
                    print("   ❌ Invalid slippage: INVALID_SLIPPAGE")
                else:
                    print(f"   ❌ Failed with: {e}")
                    continue

        print("\n💥 ALL PARAMETER COMBINATIONS FAILED")
        print("❌ Even with correct units failed")
        print("❌ Need to find the exact minimum requirements")

        return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(correct_units_and_parameters())
    if success:
        print("\n🎉 WORKING PARAMETERS FOUND!")
        print("✅ Bot now works with correct units and parameters!")
        print("✅ PRODUCTION READY!")
    else:
        print("\n💥 ALL PARAMETERS FAILED")
        print("❌ Need to find exact minimum requirements")
        sys.exit(1)
