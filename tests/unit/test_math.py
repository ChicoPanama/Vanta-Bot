"""
Unit tests for core mathematical functions.

Tests the authoritative scaling functions and mathematical operations
to ensure no double-scaling issues and correct calculations.
"""

import pytest
from decimal import Decimal
from src.core.math import (
    to_trade_units, from_trade_units, validate_scaling_invariant,
    get_max_safe_leverage, calculate_liquidation_price,
    USDC_6, SCALE_1E10
)


class TestScalingFunctions:
    """Test the core scaling functions."""
    
    def test_to_trade_units_basic(self):
        """Test basic scaling functionality."""
        # Test case: $100 USDC, 5x leverage, 1% slippage
        trade_units = to_trade_units(
            collateral_usdc=Decimal("100"),
            leverage_x=Decimal("5"),
            slippage_pct=Decimal("1")
        )
        
        # Expected values
        assert trade_units.initial_pos_token == 100_000_000  # $100 in 6dp
        assert trade_units.leverage == 50_000_000_000       # 5x in 1e10
        assert trade_units.position_size_usdc == 500_000_000  # $500 in 6dp
        assert trade_units.slippage == 100_000_000          # 1% in 1e10
    
    def test_to_trade_units_edge_cases(self):
        """Test edge cases and boundary conditions."""
        # Minimum values
        trade_units = to_trade_units(
            collateral_usdc=Decimal("1"),
            leverage_x=Decimal("1"),
            slippage_pct=Decimal("0")
        )
        
        assert trade_units.initial_pos_token == 1_000_000    # $1 in 6dp
        assert trade_units.leverage == 10_000_000_000       # 1x in 1e10
        assert trade_units.position_size_usdc == 1_000_000   # $1 in 6dp
        assert trade_units.slippage == 0                    # 0% slippage
    
    def test_to_trade_units_high_values(self):
        """Test high value scenarios."""
        # High leverage scenario
        trade_units = to_trade_units(
            collateral_usdc=Decimal("1000"),
            leverage_x=Decimal("100"),
            slippage_pct=Decimal("5")
        )
        
        assert trade_units.initial_pos_token == 1_000_000_000    # $1000 in 6dp
        assert trade_units.leverage == 1_000_000_000_000        # 100x in 1e10
        assert trade_units.position_size_usdc == 100_000_000_000  # $100k in 6dp
        assert trade_units.slippage == 500_000_000             # 5% in 1e10
    
    def test_to_trade_units_validation(self):
        """Test input validation."""
        # Test negative collateral
        with pytest.raises(ValueError, match="Collateral must be positive"):
            to_trade_units(Decimal("-1"), Decimal("5"), Decimal("1"))
        
        # Test zero leverage
        with pytest.raises(ValueError, match="Leverage must be positive"):
            to_trade_units(Decimal("100"), Decimal("0"), Decimal("1"))
        
        # Test negative slippage
        with pytest.raises(ValueError, match="Slippage cannot be negative"):
            to_trade_units(Decimal("100"), Decimal("5"), Decimal("-1"))
    
    def test_from_trade_units_roundtrip(self):
        """Test round-trip conversion."""
        original_collateral = Decimal("100")
        original_leverage = Decimal("5")
        original_slippage = Decimal("1")
        
        # Convert to trade units
        trade_units = to_trade_units(original_collateral, original_leverage, original_slippage)
        
        # Convert back to human units
        collateral, leverage, slippage = from_trade_units(trade_units)
        
        # Should match original values (within precision)
        assert abs(collateral - original_collateral) < Decimal("0.000001")
        assert abs(leverage - original_leverage) < Decimal("0.0000000001")
        assert abs(slippage - original_slippage) < Decimal("0.0000000001")
    
    def test_validate_scaling_invariant(self):
        """Test scaling invariant validation."""
        # Valid trade units
        trade_units = to_trade_units(Decimal("100"), Decimal("5"), Decimal("1"))
        assert validate_scaling_invariant(trade_units) is True
        
        # Invalid trade units (position size doesn't match calculation)
        from src.core.math import TradeUnits
        invalid_units = TradeUnits(
            initial_pos_token=100_000_000,
            leverage=50_000_000_000,
            position_size_usdc=999_999_999,  # Wrong value
            slippage=100_000_000
        )
        assert validate_scaling_invariant(invalid_units) is False
    
    def test_no_double_scaling(self):
        """Ensure no double-scaling occurs."""
        # Test that our scaling produces reasonable values
        trade_units = to_trade_units(Decimal("100"), Decimal("5"), Decimal("1"))
        
        # Leverage should not be > 10^15 (indicates double-scaling)
        assert trade_units.leverage < 10**15
        
        # Slippage should not be > 10^15 (indicates double-scaling)
        assert trade_units.slippage < 10**15
        
        # Position size should be reasonable
        assert trade_units.position_size_usdc < 10**15


class TestLiquidationCalculation:
    """Test liquidation price calculations."""
    
    def test_long_liquidation_price(self):
        """Test liquidation price for long positions."""
        entry_price = Decimal("50000")
        leverage = Decimal("10")
        
        liquidation_price = calculate_liquidation_price(entry_price, leverage, True)
        
        # For long: liquidation = entry_price * (1 - 1/leverage)
        expected = entry_price * (Decimal("1") - Decimal("1") / leverage)
        assert abs(liquidation_price - expected) < Decimal("0.01")
    
    def test_short_liquidation_price(self):
        """Test liquidation price for short positions."""
        entry_price = Decimal("50000")
        leverage = Decimal("10")
        
        liquidation_price = calculate_liquidation_price(entry_price, leverage, False)
        
        # For short: liquidation = entry_price * (1 + 1/leverage)
        expected = entry_price * (Decimal("1") + Decimal("1") / leverage)
        assert abs(liquidation_price - expected) < Decimal("0.01")
    
    def test_high_leverage_liquidation(self):
        """Test liquidation price with high leverage."""
        entry_price = Decimal("50000")
        leverage = Decimal("100")  # 100x leverage
        
        long_liquidation = calculate_liquidation_price(entry_price, leverage, True)
        short_liquidation = calculate_liquidation_price(entry_price, leverage, False)
        
        # High leverage should result in liquidation prices close to entry price
        assert abs(long_liquidation - entry_price) < entry_price * Decimal("0.02")  # Within 2%
        assert abs(short_liquidation - entry_price) < entry_price * Decimal("0.02")  # Within 2%


class TestMaxSafeLeverage:
    """Test maximum safe leverage calculations."""
    
    def test_max_safe_leverage_basic(self):
        """Test basic max safe leverage calculation."""
        collateral = Decimal("100")
        max_position = Decimal("1000")
        
        max_leverage = get_max_safe_leverage(collateral, max_position)
        
        assert max_leverage == Decimal("10")  # 10x leverage
    
    def test_max_safe_leverage_edge_cases(self):
        """Test edge cases for max safe leverage."""
        # Zero collateral
        max_leverage = get_max_safe_leverage(Decimal("0"), Decimal("1000"))
        assert max_leverage == Decimal("0")
        
        # Collateral equals max position
        max_leverage = get_max_safe_leverage(Decimal("100"), Decimal("100"))
        assert max_leverage == Decimal("1")
        
        # Collateral exceeds max position
        max_leverage = get_max_safe_leverage(Decimal("200"), Decimal("100"))
        assert max_leverage == Decimal("0.5")


class TestScalingConstants:
    """Test scaling constants."""
    
    def test_usdc_scaling(self):
        """Test USDC scaling constant."""
        assert USDC_6 == Decimal("1000000")  # 10^6
    
    def test_leverage_scaling(self):
        """Test leverage/slippage scaling constant."""
        assert SCALE_1E10 == Decimal("10000000000")  # 10^10
    
    def test_scaling_precision(self):
        """Test that scaling maintains precision."""
        # Test that Decimal arithmetic preserves precision
        collateral = Decimal("123.456789")
        scaled = collateral * USDC_6
        unscaled = scaled / USDC_6
        
        assert unscaled == collateral  # Exact match with Decimal
