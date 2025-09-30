"""
Unit tests for validation logic.

Tests the validation functions to ensure proper parameter validation
and business rule enforcement.
"""

from decimal import Decimal

from src.core.math import TradeUnits
from src.core.models import HumanTradeParams, OrderType, RiskLimits, TradeLimits
from src.core.validation import (
    clamp_trade_params,
    comprehensive_validation,
    validate_human_trade_params,
    validate_market_order_invariant,
    validate_risk_limits,
    validate_scaling_consistency,
    validate_trade_input,
)


class TestHumanTradeParamsValidation:
    """Test validation of human-readable trade parameters."""

    def test_valid_params(self):
        """Test validation with valid parameters."""
        params = HumanTradeParams(
            collateral_usdc=Decimal("100"),
            leverage_x=Decimal("5"),
            slippage_pct=Decimal("1"),
            pair_index=0,
            is_long=True,
            order_type=OrderType.MARKET,
        )

        errors = validate_human_trade_params(params)
        assert len(errors) == 0

    def test_invalid_collateral(self):
        """Test validation with invalid collateral."""
        # Negative collateral
        params = HumanTradeParams(
            collateral_usdc=Decimal("-10"),
            leverage_x=Decimal("5"),
            slippage_pct=Decimal("1"),
            pair_index=0,
            is_long=True,
            order_type=OrderType.MARKET,
        )

        errors = validate_human_trade_params(params)
        assert "Collateral must be positive" in errors

        # Too small collateral
        params = HumanTradeParams(
            collateral_usdc=Decimal("0.5"),
            leverage_x=Decimal("5"),
            slippage_pct=Decimal("1"),
            pair_index=0,
            is_long=True,
            order_type=OrderType.MARKET,
        )

        errors = validate_human_trade_params(params)
        assert "Minimum collateral is $1 USDC" in errors

        # Too large collateral
        params = HumanTradeParams(
            collateral_usdc=Decimal("200000"),
            leverage_x=Decimal("5"),
            slippage_pct=Decimal("1"),
            pair_index=0,
            is_long=True,
            order_type=OrderType.MARKET,
        )

        errors = validate_human_trade_params(params)
        assert "Maximum collateral is $100,000 USDC" in errors

    def test_invalid_leverage(self):
        """Test validation with invalid leverage."""
        # Zero leverage
        params = HumanTradeParams(
            collateral_usdc=Decimal("100"),
            leverage_x=Decimal("0"),
            slippage_pct=Decimal("1"),
            pair_index=0,
            is_long=True,
            order_type=OrderType.MARKET,
        )

        errors = validate_human_trade_params(params)
        assert "Leverage must be positive" in errors

        # Too high leverage
        params = HumanTradeParams(
            collateral_usdc=Decimal("100"),
            leverage_x=Decimal("1000"),
            slippage_pct=Decimal("1"),
            pair_index=0,
            is_long=True,
            order_type=OrderType.MARKET,
        )

        errors = validate_human_trade_params(params)
        assert "Maximum leverage is 500x" in errors

    def test_invalid_slippage(self):
        """Test validation with invalid slippage."""
        # Negative slippage
        params = HumanTradeParams(
            collateral_usdc=Decimal("100"),
            leverage_x=Decimal("5"),
            slippage_pct=Decimal("-1"),
            pair_index=0,
            is_long=True,
            order_type=OrderType.MARKET,
        )

        errors = validate_human_trade_params(params)
        assert "Slippage cannot be negative" in errors

        # Too high slippage
        params = HumanTradeParams(
            collateral_usdc=Decimal("100"),
            leverage_x=Decimal("5"),
            slippage_pct=Decimal("20"),
            pair_index=0,
            is_long=True,
            order_type=OrderType.MARKET,
        )

        errors = validate_human_trade_params(params)
        assert "Maximum slippage is 10%" in errors

    def test_invalid_pair_index(self):
        """Test validation with invalid pair index."""
        params = HumanTradeParams(
            collateral_usdc=Decimal("100"),
            leverage_x=Decimal("5"),
            slippage_pct=Decimal("1"),
            pair_index=-1,
            is_long=True,
            order_type=OrderType.MARKET,
        )

        errors = validate_human_trade_params(params)
        assert "Pair index must be non-negative" in errors


class TestTradeInputValidation:
    """Test validation of contract trade input."""

    def test_valid_trade_input(self):
        """Test validation with valid trade input."""
        trade_input = {
            "pairIndex": 0,
            "buy": True,
            "leverage": 50_000_000_000,  # 5x in 1e10
            "initialPosToken": 100_000_000,  # $100 in 6dp
            "positionSizeUSDC": 500_000_000,  # $500 in 6dp
            "openPrice": 0,
            "tp": 0,
            "sl": 0,
            "timestamp": 0,
        }

        limits = TradeLimits(
            minPositionSize=1_000_000,
            maxPositionSize=100_000_000_000,
            maxLeverage=500_000_000_000,
            maxSlippage=500_000_000,
            maxPairs=10,
        )

        errors = validate_trade_input(trade_input, limits)
        assert len(errors) == 0

    def test_invalid_position_size(self):
        """Test validation with invalid position size."""
        trade_input = {
            "pairIndex": 0,
            "buy": True,
            "leverage": 50_000_000_000,
            "initialPosToken": 500_000,  # Too small
            "positionSizeUSDC": 2_500_000,
            "openPrice": 0,
            "tp": 0,
            "sl": 0,
            "timestamp": 0,
        }

        limits = TradeLimits(
            minPositionSize=1_000_000,
            maxPositionSize=100_000_000_000,
            maxLeverage=500_000_000_000,
            maxSlippage=500_000_000,
            maxPairs=10,
        )

        errors = validate_trade_input(trade_input, limits)
        assert any("below minimum" in error for error in errors)

    def test_invalid_leverage(self):
        """Test validation with invalid leverage."""
        trade_input = {
            "pairIndex": 0,
            "buy": True,
            "leverage": 1_000_000_000_000,  # Too high
            "initialPosToken": 100_000_000,
            "positionSizeUSDC": 100_000_000_000,
            "openPrice": 0,
            "tp": 0,
            "sl": 0,
            "timestamp": 0,
        }

        limits = TradeLimits(
            minPositionSize=1_000_000,
            maxPositionSize=100_000_000_000,
            maxLeverage=500_000_000_000,
            maxSlippage=500_000_000,
            maxPairs=10,
        )

        errors = validate_trade_input(trade_input, limits)
        assert any("above maximum" in error for error in errors)


class TestRiskLimitsValidation:
    """Test risk limits validation."""

    def test_valid_risk_limits(self):
        """Test validation with valid risk limits."""
        params = HumanTradeParams(
            collateral_usdc=Decimal("100"),
            leverage_x=Decimal("5"),
            slippage_pct=Decimal("1"),
            pair_index=0,
            is_long=True,
            order_type=OrderType.MARKET,
        )

        risk_limits = RiskLimits(
            max_position_size_usd=Decimal("100000"),
            max_account_risk_pct=Decimal("0.10"),
            liquidation_buffer_pct=Decimal("0.05"),
            max_daily_loss_pct=Decimal("0.20"),
        )

        current_balance = Decimal("10000")  # $10k balance

        errors = validate_risk_limits(params, risk_limits, current_balance)
        assert len(errors) == 0

    def test_position_size_risk(self):
        """Test position size risk validation."""
        params = HumanTradeParams(
            collateral_usdc=Decimal("100"),
            leverage_x=Decimal("1000"),  # Very high leverage
            slippage_pct=Decimal("1"),
            pair_index=0,
            is_long=True,
            order_type=OrderType.MARKET,
        )

        risk_limits = RiskLimits(
            max_position_size_usd=Decimal("100000"),
            max_account_risk_pct=Decimal("0.10"),
            liquidation_buffer_pct=Decimal("0.05"),
            max_daily_loss_pct=Decimal("0.20"),
        )

        current_balance = Decimal("10000")

        errors = validate_risk_limits(params, risk_limits, current_balance)
        assert any("Position size" in error for error in errors)

    def test_account_risk(self):
        """Test account risk validation."""
        params = HumanTradeParams(
            collateral_usdc=Decimal("5000"),  # 50% of account
            leverage_x=Decimal("5"),
            slippage_pct=Decimal("1"),
            pair_index=0,
            is_long=True,
            order_type=OrderType.MARKET,
        )

        risk_limits = RiskLimits(
            max_position_size_usd=Decimal("100000"),
            max_account_risk_pct=Decimal("0.10"),  # Max 10% risk
            liquidation_buffer_pct=Decimal("0.05"),
            max_daily_loss_pct=Decimal("0.20"),
        )

        current_balance = Decimal("10000")

        errors = validate_risk_limits(params, risk_limits, current_balance)
        assert any("Account risk" in error for error in errors)


class TestParameterClamping:
    """Test parameter clamping functionality."""

    def test_clamp_basic(self):
        """Test basic parameter clamping."""
        params = HumanTradeParams(
            collateral_usdc=Decimal("200"),  # Over limit
            leverage_x=Decimal("1000"),  # Over limit
            slippage_pct=Decimal("20"),  # Over limit
            pair_index=0,
            is_long=True,
            order_type=OrderType.MARKET,
        )

        limits = TradeLimits(
            minPositionSize=1_000_000,
            maxPositionSize=100_000_000_000,
            maxLeverage=500_000_000_000,
            maxSlippage=500_000_000,
            maxPairs=10,
        )

        risk_limits = RiskLimits(
            max_position_size_usd=Decimal("100000"),
            max_account_risk_pct=Decimal("0.10"),
            liquidation_buffer_pct=Decimal("0.05"),
            max_daily_loss_pct=Decimal("0.20"),
        )

        current_balance = Decimal("10000")

        clamped_params = clamp_trade_params(
            params, limits, risk_limits, current_balance
        )

        # Should be clamped to safe limits
        assert clamped_params.collateral_usdc <= Decimal("100000")
        assert clamped_params.leverage_x <= Decimal("500")
        assert clamped_params.slippage_pct <= Decimal("10")

    def test_clamp_within_limits(self):
        """Test clamping when parameters are already within limits."""
        params = HumanTradeParams(
            collateral_usdc=Decimal("100"),
            leverage_x=Decimal("5"),
            slippage_pct=Decimal("1"),
            pair_index=0,
            is_long=True,
            order_type=OrderType.MARKET,
        )

        limits = TradeLimits(
            minPositionSize=1_000_000,
            maxPositionSize=100_000_000_000,
            maxLeverage=500_000_000_000,
            maxSlippage=500_000_000,
            maxPairs=10,
        )

        risk_limits = RiskLimits(
            max_position_size_usd=Decimal("100000"),
            max_account_risk_pct=Decimal("0.10"),
            liquidation_buffer_pct=Decimal("0.05"),
            max_daily_loss_pct=Decimal("0.20"),
        )

        current_balance = Decimal("10000")

        clamped_params = clamp_trade_params(
            params, limits, risk_limits, current_balance
        )

        # Should remain unchanged
        assert clamped_params.collateral_usdc == params.collateral_usdc
        assert clamped_params.leverage_x == params.leverage_x
        assert clamped_params.slippage_pct == params.slippage_pct


class TestScalingConsistencyValidation:
    """Test scaling consistency validation."""

    def test_valid_scaling(self):
        """Test validation with consistent scaling."""
        trade_units = TradeUnits(
            initial_pos_token=100_000_000,
            leverage=50_000_000_000,
            position_size_usdc=500_000_000,
            slippage=100_000_000,
        )

        assert validate_scaling_consistency(trade_units) is True

    def test_double_scaled_leverage(self):
        """Test detection of double-scaled leverage."""
        trade_units = TradeUnits(
            initial_pos_token=100_000_000,
            leverage=50_000_000_000_000_000,  # Double-scaled
            position_size_usdc=500_000_000,
            slippage=100_000_000,
        )

        assert validate_scaling_consistency(trade_units) is False

    def test_double_scaled_slippage(self):
        """Test detection of double-scaled slippage."""
        trade_units = TradeUnits(
            initial_pos_token=100_000_000,
            leverage=50_000_000_000,
            position_size_usdc=500_000_000,
            slippage=100_000_000_000_000_000,  # Double-scaled
        )

        assert validate_scaling_consistency(trade_units) is False


class TestMarketOrderInvariant:
    """Test market order invariant validation."""

    def test_valid_market_order(self):
        """Test validation with valid market order."""
        trade_input = {
            "pairIndex": 0,
            "buy": True,
            "leverage": 50_000_000_000,
            "initialPosToken": 100_000_000,
            "positionSizeUSDC": 500_000_000,
            "openPrice": 0,  # Market order
            "tp": 0,
            "sl": 0,
            "timestamp": 0,
        }

        assert validate_market_order_invariant(trade_input) is True

    def test_invalid_market_order(self):
        """Test validation with invalid market order."""
        trade_input = {
            "pairIndex": 0,
            "buy": True,
            "leverage": 50_000_000_000,
            "initialPosToken": 100_000_000,
            "positionSizeUSDC": 500_000_000,
            "openPrice": 50000,  # Not a market order
            "tp": 0,
            "sl": 0,
            "timestamp": 0,
        }

        assert validate_market_order_invariant(trade_input) is False


class TestComprehensiveValidation:
    """Test comprehensive validation function."""

    def test_comprehensive_validation_success(self):
        """Test comprehensive validation with valid parameters."""
        params = HumanTradeParams(
            collateral_usdc=Decimal("100"),
            leverage_x=Decimal("5"),
            slippage_pct=Decimal("1"),
            pair_index=0,
            is_long=True,
            order_type=OrderType.MARKET,
        )

        limits = TradeLimits(
            minPositionSize=1_000_000,
            maxPositionSize=100_000_000_000,
            maxLeverage=500_000_000_000,
            maxSlippage=500_000_000,
            maxPairs=10,
        )

        risk_limits = RiskLimits(
            max_position_size_usd=Decimal("100000"),
            max_account_risk_pct=Decimal("0.10"),
            liquidation_buffer_pct=Decimal("0.05"),
            max_daily_loss_pct=Decimal("0.20"),
        )

        current_balance = Decimal("10000")

        is_valid, errors, clamped_params = comprehensive_validation(
            params, limits, risk_limits, current_balance
        )

        assert is_valid is True
        assert len(errors) == 0
        assert clamped_params is not None

    def test_comprehensive_validation_failure(self):
        """Test comprehensive validation with invalid parameters."""
        params = HumanTradeParams(
            collateral_usdc=Decimal("-100"),  # Invalid
            leverage_x=Decimal("5"),
            slippage_pct=Decimal("1"),
            pair_index=0,
            is_long=True,
            order_type=OrderType.MARKET,
        )

        limits = TradeLimits(
            minPositionSize=1_000_000,
            maxPositionSize=100_000_000_000,
            maxLeverage=500_000_000_000,
            maxSlippage=500_000_000,
            maxPairs=10,
        )

        risk_limits = RiskLimits(
            max_position_size_usd=Decimal("100000"),
            max_account_risk_pct=Decimal("0.10"),
            liquidation_buffer_pct=Decimal("0.05"),
            max_daily_loss_pct=Decimal("0.20"),
        )

        current_balance = Decimal("10000")

        is_valid, errors, clamped_params = comprehensive_validation(
            params, limits, risk_limits, current_balance
        )

        assert is_valid is False
        assert len(errors) > 0
        assert clamped_params is None
