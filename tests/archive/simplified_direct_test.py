#!/usr/bin/env python3
"""
Simplified Direct Contract Test

This script demonstrates the direct contract approach with proper scaling,
working around the fact that the contract is currently paused.
"""

import json
import logging
from decimal import Decimal

from web3 import Web3

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def demonstrate_proper_scaling():
    """Demonstrate the correct scaling approach that bypasses SDK issues."""

    logger.info("🎯 DEMONSTRATING PROPER SCALING (Bypassing SDK Double-Scaling)")
    logger.info("=" * 70)

    # Connect to Base
    w3 = Web3(Web3.HTTPProvider("https://mainnet.base.org"))
    if not w3.is_connected():
        logger.error("Failed to connect to Base network")
        return

    # Load ABI and initialize contract
    with open("config/abis/Trading.json") as f:
        data = json.load(f)

    trading_addr = "0x5FF292d70bA9cD9e7CCb313782811b3D7120535f"
    contract = w3.eth.contract(address=trading_addr, abi=data["abi"])

    # Check contract status
    try:
        paused = contract.functions.paused().call()
        operator = contract.functions.operator().call()
        pair_infos = contract.functions.pairInfos().call()

        logger.info("Contract Status:")
        logger.info(f"  Address: {trading_addr}")
        logger.info(f"  Paused: {paused}")
        logger.info(f"  Operator: {operator}")
        logger.info(f"  PairInfos: {pair_infos}")

    except Exception as e:
        logger.error(f"Failed to get contract info: {e}")
        return

    # Scaling constants
    USDC_6 = Decimal(10) ** 6  # USDC has 6 decimals
    SCALE_1E10 = Decimal(10) ** 10  # Leverage/slippage scaling

    # Test scenarios
    test_cases = [
        {
            "name": "Control Test - Known Good Values",
            "collateral": Decimal("100"),  # $100 USDC
            "leverage": Decimal("5"),  # 5x leverage
            "slippage_pct": Decimal("1.0"),  # 1.00%
        },
        {
            "name": "Minimum Viable Values",
            "collateral": Decimal("10"),  # $10 USDC
            "leverage": Decimal("1"),  # 1x leverage
            "slippage_pct": Decimal("0.1"),  # 0.1%
        },
        {
            "name": "High Leverage Test",
            "collateral": Decimal("50"),  # $50 USDC
            "leverage": Decimal("20"),  # 20x leverage
            "slippage_pct": Decimal("2.0"),  # 2.0%
        },
    ]

    logger.info("\n🔧 PROPER SCALING DEMONSTRATION")
    logger.info("=" * 70)

    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\n--- Test Case {i}: {test_case['name']} ---")

        collateral = test_case["collateral"]
        leverage = test_case["leverage"]
        slippage_pct = test_case["slippage_pct"]

        logger.info("Input values:")
        logger.info(f"  Collateral: {collateral} USDC")
        logger.info(f"  Leverage: {leverage}x")
        logger.info(f"  Slippage: {slippage_pct}%")

        # PROPER SCALING (Single scaling - what should happen)
        initial_pos_token = int(collateral * USDC_6)
        leverage_scaled = int(leverage * SCALE_1E10)
        position_size_usdc = (initial_pos_token * leverage_scaled) // int(SCALE_1E10)
        slippage_scaled = int((slippage_pct / Decimal(100)) * SCALE_1E10)

        logger.info("Properly scaled values:")
        logger.info(f"  initialPosToken: {initial_pos_token:,} (6dp)")
        logger.info(f"  leverage: {leverage_scaled:,} (1e10)")
        logger.info(
            f"  positionSizeUSDC: {position_size_usdc:,} (6dp = ${position_size_usdc / 1e6:.2f})"
        )
        logger.info(
            f"  slippage: {slippage_scaled:,} (1e10 = {slippage_scaled / 1e10:.2f}%)"
        )

        # Build trade struct (as it would be for openTrade)
        trade_struct = {
            "trader": "0x1234567890123456789012345678901234567890",  # Placeholder
            "pairIndex": 0,
            "index": 0,
            "initialPosToken": initial_pos_token,
            "positionSizeUSDC": position_size_usdc,
            "openPrice": 0,  # Market order
            "buy": True,  # Long position
            "leverage": leverage_scaled,
            "tp": 0,  # No take profit
            "sl": 0,  # No stop loss
            "timestamp": 0,
        }

        logger.info("Trade struct ready for openTrade:")
        for key, value in trade_struct.items():
            if isinstance(value, bool):
                logger.info(f"  {key}: {value}")
            elif isinstance(value, str):
                logger.info(f"  {key}: {value}")
            else:
                logger.info(f"  {key}: {value:,}")

        # Show what would be passed to openTrade
        logger.info("openTrade parameters:")
        logger.info("  trade_struct: [as above]")
        logger.info("  order_type: 0 (MARKET)")
        logger.info(f"  slippage: {slippage_scaled:,}")


def demonstrate_sdk_issue():
    """Demonstrate what happens with SDK double-scaling."""

    logger.info("\n❌ SDK DOUBLE-SCALING ISSUE DEMONSTRATION")
    logger.info("=" * 70)

    # Example: You want to trade $100 with 5x leverage, 1% slippage
    collateral = Decimal("100")
    leverage = Decimal("5")
    slippage_pct = Decimal("1.0")

    USDC_6 = Decimal(10) ** 6
    SCALE_1E10 = Decimal(10) ** 10

    logger.info("Your intention:")
    logger.info(f"  Collateral: {collateral} USDC")
    logger.info(f"  Leverage: {leverage}x")
    logger.info(f"  Slippage: {slippage_pct}%")

    # Step 1: You pre-scale (thinking you need to)
    logger.info("\nStep 1: You pre-scale (thinking you need to):")
    pre_scaled_collateral = int(collateral * USDC_6)
    pre_scaled_leverage = int(leverage * SCALE_1E10)
    pre_scaled_slippage = int((slippage_pct / Decimal(100)) * SCALE_1E10)

    logger.info(f"  Pre-scaled collateral: {pre_scaled_collateral:,}")
    logger.info(f"  Pre-scaled leverage: {pre_scaled_leverage:,}")
    logger.info(f"  Pre-scaled slippage: {pre_scaled_slippage:,}")

    # Step 2: SDK scales AGAIN (double-scaling)
    logger.info("\nStep 2: SDK scales AGAIN (double-scaling):")
    double_scaled_collateral = int(Decimal(pre_scaled_collateral) * USDC_6)
    double_scaled_leverage = int(Decimal(pre_scaled_leverage) * SCALE_1E10)
    double_scaled_slippage = int(Decimal(pre_scaled_slippage) * SCALE_1E10)

    logger.info(f"  Double-scaled collateral: {double_scaled_collateral:,}")
    logger.info(f"  Double-scaled leverage: {double_scaled_leverage:,}")
    logger.info(f"  Double-scaled slippage: {double_scaled_slippage:,}")

    # Show the damage
    logger.info("\n💥 THE DAMAGE:")
    logger.info(
        f"  Collateral: {collateral} USDC → {double_scaled_collateral / USDC_6:.2f} USDC"
    )
    logger.info(f"  Leverage: {leverage}x → {double_scaled_leverage / SCALE_1E10:.1f}x")
    logger.info(
        f"  Slippage: {slippage_pct}% → {double_scaled_slippage / SCALE_1E10:.6f}%"
    )

    # Check against typical limits
    max_slippage = 500_000_000  # 5% in 1e10 scale
    logger.info("\n🚨 VALIDATION ISSUES:")
    logger.info(f"  Max allowed slippage: {max_slippage:,} (5%)")
    logger.info(f"  Your slippage becomes: {double_scaled_slippage:,}")
    logger.info(f"  Exceeds max by: {double_scaled_slippage - max_slippage:,}")
    logger.info("  Result: INVALID_SLIPPAGE error!")


def show_solution_summary():
    """Show the complete solution summary."""

    logger.info("\n🛠️  COMPLETE SOLUTION SUMMARY")
    logger.info("=" * 70)

    logger.info("PROBLEM IDENTIFIED:")
    logger.info("  1. SDK auto-scales amounts (expects human units)")
    logger.info("  2. You pre-scale amounts (thinking you need to)")
    logger.info("  3. Result: Double-scaling → Wrong values → INVALID_SLIPPAGE")

    logger.info("\nSOLUTION STEPS:")
    steps = [
        "1. Stop pre-scaling - pass human values only to SDK",
        "2. If SDK still double-scales, bypass it entirely",
        "3. Use direct contract calls with proper single scaling",
        "4. Scale once: collateral*1e6, leverage*1e10, slippage*1e10",
        "5. Validate slippage <= _MAX_SLIPPAGE() from contract",
        "6. Use staticcall before spending gas",
        "7. Test with known-good values first",
    ]

    for step in steps:
        logger.info(f"  {step}")

    logger.info("\nIMPLEMENTATION:")
    logger.info("  ✅ Use practical_direct_contract_test.py as template")
    logger.info("  ✅ Replace SDK calls with direct contract calls")
    logger.info("  ✅ Scale parameters once, not twice")
    logger.info("  ✅ Validate limits from on-chain data")

    logger.info("\nTESTING:")
    logger.info("  ✅ Run with known-good values first")
    logger.info("  ✅ Compare results with SDK approach")
    logger.info("  ✅ If direct works but SDK fails → double-scaling confirmed")


def main():
    """Main demonstration function."""

    logger.info("🎯 SIMPLIFIED DIRECT CONTRACT TEST")
    logger.info("Demonstrating proper scaling vs SDK double-scaling")

    # Demonstrate proper scaling
    demonstrate_proper_scaling()

    # Demonstrate SDK issue
    demonstrate_sdk_issue()

    # Show solution summary
    show_solution_summary()

    logger.info("\n🚀 NEXT STEPS:")
    logger.info("  1. Apply this scaling approach to your actual trading code")
    logger.info("  2. Replace SDK calls with direct contract calls")
    logger.info("  3. Test with small amounts first")
    logger.info("  4. If it works, you've solved the double-scaling issue!")


if __name__ == "__main__":
    main()
