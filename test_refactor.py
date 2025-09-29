#!/usr/bin/env python3
"""
Quick test script to verify the refactored architecture works.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from decimal import Decimal
from src.core.models import HumanTradeParams, OrderType
from src.core.math import to_trade_units
from src.core.validation import validate_human_trade_params

def test_core_functionality():
    """Test the core refactored functionality."""
    print("🧪 Testing Refactored Architecture")
    print("=" * 50)
    
    # Test 1: Core math functions
    print("1. Testing single-scaling functions...")
    trade_units = to_trade_units(
        collateral_usdc=Decimal("10"),
        leverage_x=Decimal("2"),
        slippage_pct=Decimal("1")
    )
    
    print(f"   Collateral: $10 → {trade_units.initial_pos_token} (6dp)")
    print(f"   Leverage: 2x → {trade_units.leverage} (1e10)")
    print(f"   Position Size: $20 → {trade_units.position_size_usdc} (6dp)")
    print(f"   Slippage: 1% → {trade_units.slippage} (1e10)")
    
    # Verify scaling
    expected_position = (trade_units.initial_pos_token * trade_units.leverage) // (10**10)
    if trade_units.position_size_usdc == expected_position:
        print("   ✅ Scaling invariant verified")
    else:
        print(f"   ❌ Scaling invariant failed: {trade_units.position_size_usdc} != {expected_position}")
        return False
    
    # Test 2: Parameter validation
    print("\n2. Testing parameter validation...")
    params = HumanTradeParams(
        collateral_usdc=Decimal("10"),
        leverage_x=Decimal("2"),
        slippage_pct=Decimal("1"),
        pair_index=0,
        is_long=True,
        order_type=OrderType.MARKET
    )
    
    errors = validate_human_trade_params(params)
    if not errors:
        print("   ✅ Parameter validation passed")
    else:
        print(f"   ❌ Parameter validation failed: {errors}")
        return False
    
    # Test 3: Double-scaling detection
    print("\n3. Testing double-scaling detection...")
    from src.core.math import TradeUnits
    
    # Simulate double-scaled values
    double_scaled = TradeUnits(
        initial_pos_token=10_000_000,
        leverage=20_000_000_000,
        position_size_usdc=20_000_000,
        slippage=100_000_000_000_000_000  # Double-scaled
    )
    
    from src.core.validation import validate_scaling_consistency
    if not validate_scaling_consistency(double_scaled):
        print("   ✅ Double-scaling detection works")
    else:
        print("   ❌ Double-scaling detection failed")
        return False
    
    print("\n🎉 All core functionality tests passed!")
    print("   The refactored architecture is working correctly.")
    return True

if __name__ == "__main__":
    success = test_core_functionality()
    sys.exit(0 if success else 1)
