"""Tests for risk calculation primitives."""

import pytest
from decimal import Decimal
from src.services.risk.primitives import (
    calculate_pnl, calculate_liquidation_price, calculate_margin_ratio,
    calculate_risk_score, calculate_position_metrics, PositionInfo
)


class TestPnLCalculation:
    """Test PnL calculations."""
    
    def test_long_position_profit(self):
        """Test long position with profit."""
        entry_price = Decimal('50000')
        current_price = Decimal('51000')
        size = Decimal('1000')
        
        pnl = calculate_pnl(entry_price, current_price, size, 'long')
        expected = (current_price - entry_price) / entry_price * size
        assert pnl == expected
        assert pnl > 0  # Profit
    
    def test_long_position_loss(self):
        """Test long position with loss."""
        entry_price = Decimal('50000')
        current_price = Decimal('49000')
        size = Decimal('1000')
        
        pnl = calculate_pnl(entry_price, current_price, size, 'long')
        assert pnl < 0  # Loss
    
    def test_short_position_profit(self):
        """Test short position with profit."""
        entry_price = Decimal('50000')
        current_price = Decimal('49000')
        size = Decimal('1000')
        
        pnl = calculate_pnl(entry_price, current_price, size, 'short')
        expected = (entry_price - current_price) / entry_price * size
        assert pnl == expected
        assert pnl > 0  # Profit
    
    def test_short_position_loss(self):
        """Test short position with loss."""
        entry_price = Decimal('50000')
        current_price = Decimal('51000')
        size = Decimal('1000')
        
        pnl = calculate_pnl(entry_price, current_price, size, 'short')
        assert pnl < 0  # Loss
    
    def test_invalid_side_raises_error(self):
        """Test that invalid side raises error."""
        with pytest.raises(ValueError):
            calculate_pnl(Decimal('50000'), Decimal('51000'), Decimal('1000'), 'invalid')


class TestLiquidationPrice:
    """Test liquidation price calculations."""
    
    def test_long_liquidation_price(self):
        """Test long position liquidation price."""
        entry_price = Decimal('50000')
        leverage = Decimal('10')
        fee_rate = Decimal('0.001')
        maintenance_margin = Decimal('0.05')
        
        liq_price = calculate_liquidation_price(
            entry_price, leverage, fee_rate, maintenance_margin, 'long'
        )
        
        # For long positions, liquidation price should be below entry price
        assert liq_price < entry_price
        assert liq_price > 0
    
    def test_short_liquidation_price(self):
        """Test short position liquidation price."""
        entry_price = Decimal('50000')
        leverage = Decimal('10')
        fee_rate = Decimal('0.001')
        maintenance_margin = Decimal('0.05')
        
        liq_price = calculate_liquidation_price(
            entry_price, leverage, fee_rate, maintenance_margin, 'short'
        )
        
        # For short positions, liquidation price should be above entry price
        assert liq_price > entry_price
        assert liq_price > 0
    
    def test_higher_leverage_lower_liquidation_price(self):
        """Test that higher leverage results in liquidation price closer to entry."""
        entry_price = Decimal('50000')
        fee_rate = Decimal('0.001')
        maintenance_margin = Decimal('0.05')
        
        liq_price_5x = calculate_liquidation_price(
            entry_price, Decimal('5'), fee_rate, maintenance_margin, 'long'
        )
        liq_price_10x = calculate_liquidation_price(
            entry_price, Decimal('10'), fee_rate, maintenance_margin, 'long'
        )
        
        # Higher leverage should result in liquidation price closer to entry price
        assert abs(liq_price_10x - entry_price) < abs(liq_price_5x - entry_price)


class TestMarginRatio:
    """Test margin ratio calculations."""
    
    def test_long_margin_ratio_decreases_with_price_drop(self):
        """Test that margin ratio decreases as price drops for long positions."""
        entry_price = Decimal('50000')
        leverage = Decimal('10')
        
        # Price at entry
        margin_at_entry = calculate_margin_ratio(entry_price, entry_price, leverage, 'long')
        assert margin_at_entry == Decimal('1')  # 100% margin at entry
        
        # Price drops
        margin_at_lower = calculate_margin_ratio(entry_price, Decimal('45000'), leverage, 'long')
        assert margin_at_lower < margin_at_entry
    
    def test_short_margin_ratio_decreases_with_price_rise(self):
        """Test that margin ratio decreases as price rises for short positions."""
        entry_price = Decimal('50000')
        leverage = Decimal('10')
        
        # Price at entry
        margin_at_entry = calculate_margin_ratio(entry_price, entry_price, leverage, 'short')
        assert margin_at_entry == Decimal('1')  # 100% margin at entry
        
        # Price rises
        margin_at_higher = calculate_margin_ratio(entry_price, Decimal('55000'), leverage, 'short')
        assert margin_at_higher < margin_at_entry


class TestRiskScore:
    """Test risk score calculations."""
    
    def test_risk_score_increases_with_leverage(self):
        """Test that risk score increases with higher leverage."""
        base_position = PositionInfo(
            entry_price=Decimal('50000'),
            current_price=Decimal('50000'),
            size=Decimal('1000'),
            leverage=Decimal('5'),
            side='long'
        )
        
        high_leverage_position = PositionInfo(
            entry_price=Decimal('50000'),
            current_price=Decimal('50000'),
            size=Decimal('1000'),
            leverage=Decimal('20'),
            side='long'
        )
        
        base_risk = calculate_risk_score(base_position)
        high_risk = calculate_risk_score(high_leverage_position)
        
        assert high_risk > base_risk
    
    def test_risk_score_increases_near_liquidation(self):
        """Test that risk score increases as position approaches liquidation."""
        entry_price = Decimal('50000')
        leverage = Decimal('10')
        size = Decimal('1000')
        
        # Position at entry
        position_at_entry = PositionInfo(
            entry_price=entry_price,
            current_price=entry_price,
            size=size,
            leverage=leverage,
            side='long'
        )
        
        # Position near liquidation
        liq_price = calculate_liquidation_price(entry_price, leverage, Decimal('0.001'), Decimal('0.05'), 'long')
        position_near_liq = PositionInfo(
            entry_price=entry_price,
            current_price=liq_price * Decimal('1.01'),  # Just above liquidation
            size=size,
            leverage=leverage,
            side='long'
        )
        
        risk_at_entry = calculate_risk_score(position_at_entry)
        risk_near_liq = calculate_risk_score(position_near_liq)
        
        assert risk_near_liq > risk_at_entry
    
    def test_risk_score_bounded(self):
        """Test that risk score is bounded between 0 and 1."""
        position = PositionInfo(
            entry_price=Decimal('50000'),
            current_price=Decimal('50000'),
            size=Decimal('1000'),
            leverage=Decimal('10'),
            side='long'
        )
        
        risk_score = calculate_risk_score(position)
        assert Decimal('0') <= risk_score <= Decimal('1')


class TestPositionMetrics:
    """Test comprehensive position metrics."""
    
    def test_position_metrics_calculation(self):
        """Test that position metrics are calculated correctly."""
        position = PositionInfo(
            entry_price=Decimal('50000'),
            current_price=Decimal('51000'),
            size=Decimal('1000'),
            leverage=Decimal('10'),
            side='long'
        )
        
        metrics = calculate_position_metrics(position)
        
        # Verify all metrics are present
        assert hasattr(metrics, 'pnl')
        assert hasattr(metrics, 'pnl_percentage')
        assert hasattr(metrics, 'liquidation_price')
        assert hasattr(metrics, 'margin_ratio')
        assert hasattr(metrics, 'risk_score')
        
        # Verify PnL is positive for profitable position
        assert metrics.pnl > 0
        assert metrics.pnl_percentage > 0
        
        # Verify liquidation price is below entry for long position
        assert metrics.liquidation_price < position.entry_price
        
        # Verify risk score is bounded
        assert Decimal('0') <= metrics.risk_score <= Decimal('1')
