#!/usr/bin/env python3
"""
SDK vs Direct Contract Comparison

This script demonstrates the difference between:
1. SDK approach (with double-scaling issues)
2. Direct contract approach (proper single scaling)

Shows exactly where the SDK is going wrong and how to fix it.
"""

import json
from decimal import Decimal
from web3 import Web3
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def demonstrate_scaling_issue():
    """Demonstrate the SDK double-scaling issue with concrete examples."""
    
    logger.info("🔍 DEMONSTRATING SDK DOUBLE-SCALING ISSUE")
    logger.info("="*60)
    
    # Example inputs (human-readable)
    collateral_usdc = Decimal("100")    # $100 USDC
    leverage = Decimal("5")             # 5x leverage  
    slippage_pct = Decimal("1.0")       # 1.00%
    
    # Scaling constants
    USDC_6 = Decimal(10) ** 6      # USDC has 6 decimals
    SCALE_1E10 = Decimal(10) ** 10  # Leverage/slippage scaling
    
    logger.info(f"INPUT VALUES:")
    logger.info(f"  Collateral: {collateral_usdc} USDC")
    logger.info(f"  Leverage: {leverage}x")
    logger.info(f"  Slippage: {slippage_pct}%")
    
    # CORRECT APPROACH (Direct Contract - Single Scaling)
    logger.info(f"\n✅ CORRECT APPROACH (Direct Contract):")
    
    # Scale once to contract units
    initial_pos_token_correct = int(collateral_usdc * USDC_6)
    leverage_scaled_correct = int(leverage * SCALE_1E10)
    position_size_correct = (initial_pos_token_correct * leverage_scaled_correct) // int(SCALE_1E10)
    slippage_scaled_correct = int((slippage_pct / Decimal(100)) * SCALE_1E10)
    
    logger.info(f"  initialPosToken: {initial_pos_token_correct:,} (6dp)")
    logger.info(f"  leverage: {leverage_scaled_correct:,} (1e10)")
    logger.info(f"  positionSizeUSDC: {position_size_correct:,} (6dp)")
    logger.info(f"  slippage: {slippage_scaled_correct:,} (1e10)")
    
    # INCORRECT APPROACH (SDK Double-Scaling)
    logger.info(f"\n❌ INCORRECT APPROACH (SDK Double-Scaling):")
    
    # Step 1: You pre-scale (thinking you need to)
    pre_scaled_collateral = int(collateral_usdc * USDC_6)
    pre_scaled_leverage = int(leverage * SCALE_1E10)
    pre_scaled_slippage = int((slippage_pct / Decimal(100)) * SCALE_1E10)
    
    logger.info(f"  Pre-scaled collateral: {pre_scaled_collateral:,}")
    logger.info(f"  Pre-scaled leverage: {pre_scaled_leverage:,}")
    logger.info(f"  Pre-scaled slippage: {pre_scaled_slippage:,}")
    
    # Step 2: SDK scales AGAIN (double-scaling)
    # This is what the SDK does internally
    double_scaled_collateral = int(Decimal(pre_scaled_collateral) * USDC_6)
    double_scaled_leverage = int(Decimal(pre_scaled_leverage) * SCALE_1E10)
    double_scaled_slippage = int(Decimal(pre_scaled_slippage) * SCALE_1E10)
    
    logger.info(f"  SDK double-scales to:")
    logger.info(f"    initialPosToken: {double_scaled_collateral:,} (WRONG!)")
    logger.info(f"    leverage: {double_scaled_leverage:,} (WRONG!)")
    logger.info(f"    slippage: {double_scaled_slippage:,} (WRONG!)")
    
    # Show the damage
    logger.info(f"\n💥 THE DAMAGE:")
    logger.info(f"  Collateral: {collateral_usdc} → {double_scaled_collateral / USDC_6:.2f} USDC")
    logger.info(f"  Leverage: {leverage}x → {double_scaled_leverage / SCALE_1E10:.1f}x")
    logger.info(f"  Slippage: {slippage_pct}% → {double_scaled_slippage / SCALE_1E10:.6f}%")
    
    return {
        "correct": {
            "initial_pos_token": initial_pos_token_correct,
            "leverage": leverage_scaled_correct,
            "position_size": position_size_correct,
            "slippage": slippage_scaled_correct
        },
        "incorrect": {
            "initial_pos_token": double_scaled_collateral,
            "leverage": double_scaled_leverage,
            "slippage": double_scaled_slippage
        }
    }

def show_validation_issues():
    """Show why INVALID_SLIPPAGE occurs with double-scaling."""
    
    logger.info(f"\n🚨 WHY INVALID_SLIPPAGE OCCURS")
    logger.info("="*60)
    
    # Example: You want 1% slippage
    desired_slippage = Decimal("1.0")  # 1%
    SCALE_1E10 = Decimal(10) ** 10
    
    # Correct scaling
    correct_slippage = int((desired_slippage / Decimal(100)) * SCALE_1E10)
    
    # Double scaling (what SDK does)
    pre_scaled = int((desired_slippage / Decimal(100)) * SCALE_1E10)
    double_scaled = int(Decimal(pre_scaled) * SCALE_1E10)
    
    logger.info(f"Desired slippage: {desired_slippage}%")
    logger.info(f"Correct value: {correct_slippage:,} (1e10 scale)")
    logger.info(f"Double-scaled: {double_scaled:,} (1e10 scale)")
    
    # Check against typical max slippage (5% = 500,000,000 in 1e10 scale)
    max_slippage = 500_000_000  # 5% in 1e10 scale
    
    logger.info(f"Max allowed slippage: {max_slippage:,}")
    logger.info(f"Correct slippage valid: {correct_slippage <= max_slippage}")
    logger.info(f"Double-scaled valid: {double_scaled <= max_slippage}")
    
    if double_scaled > max_slippage:
        logger.error(f"❌ Double-scaled slippage EXCEEDS max by {double_scaled - max_slippage:,}")
        logger.error("   This causes INVALID_SLIPPAGE error!")

def show_solution_approach():
    """Show the step-by-step solution approach."""
    
    logger.info(f"\n🛠️  SOLUTION APPROACH")
    logger.info("="*60)
    
    steps = [
        "1. Stop pre-scaling your inputs - pass human values only",
        "2. Let the contract handle scaling internally",
        "3. If SDK still double-scales, bypass it entirely",
        "4. Use direct contract calls with proper scaling (once)",
        "5. Validate limits from contract before trading",
        "6. Use staticcall to test before spending gas"
    ]
    
    for step in steps:
        logger.info(f"  {step}")
    
    logger.info(f"\n📋 IMPLEMENTATION CHECKLIST:")
    checklist = [
        "✅ Pass human units to SDK (no pre-scaling)",
        "✅ Check if SDK has 'use_base_units' or similar flag",
        "✅ If still fails, use direct contract calls",
        "✅ Scale once: collateral * 1e6, leverage * 1e10, slippage * 1e10",
        "✅ Validate slippage <= _MAX_SLIPPAGE()",
        "✅ Use staticcall before gas spending",
        "✅ Test with known-good values first"
    ]
    
    for item in checklist:
        logger.info(f"  {item}")

def main():
    """Main demonstration function."""
    
    logger.info("🎯 SDK vs Direct Contract Comparison")
    logger.info("Demonstrating the double-scaling issue and solution")
    
    # Demonstrate the scaling issue
    scaling_comparison = demonstrate_scaling_issue()
    
    # Show validation issues
    show_validation_issues()
    
    # Show solution approach
    show_solution_approach()
    
    # Save comparison data
    with open("sdk_vs_direct_comparison.json", "w") as f:
        json.dump(scaling_comparison, f, indent=2)
    
    logger.info(f"\n💾 Comparison data saved to: sdk_vs_direct_comparison.json")
    logger.info(f"\n🚀 Next steps:")
    logger.info(f"  1. Run: python practical_direct_contract_test.py")
    logger.info(f"  2. Compare results with your SDK tests")
    logger.info(f"  3. If direct approach works, you've proven the double-scaling issue")

if __name__ == "__main__":
    main()
