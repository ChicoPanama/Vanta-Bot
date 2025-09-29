"""
Validation logic for trading parameters and business rules.

This module enforces all validation rules and business invariants
to ensure safe and correct trading operations.
"""

from typing import Optional, List
from decimal import Decimal
import logging

from .models import TradeInput, TradeLimits, HumanTradeParams, RiskLimits
from .math import to_trade_units, TradeUnits

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


def validate_human_trade_params(params: HumanTradeParams) -> List[str]:
    """
    Validate human-readable trade parameters.
    
    Args:
        params: Human trade parameters to validate
    
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Collateral validation
    if params.collateral_usdc <= 0:
        errors.append("Collateral must be positive")
    elif params.collateral_usdc < Decimal("1"):
        errors.append("Minimum collateral is $1 USDC")
    elif params.collateral_usdc > Decimal("100000"):
        errors.append("Maximum collateral is $100,000 USDC")
    
    # Leverage validation
    if params.leverage_x <= 0:
        errors.append("Leverage must be positive")
    elif params.leverage_x < Decimal("1"):
        errors.append("Minimum leverage is 1x")
    elif params.leverage_x > Decimal("500"):
        errors.append("Maximum leverage is 500x")
    
    # Slippage validation
    if params.slippage_pct < 0:
        errors.append("Slippage cannot be negative")
    elif params.slippage_pct > Decimal("10"):
        errors.append("Maximum slippage is 10%")
    
    # Pair index validation
    if params.pair_index < 0:
        errors.append("Pair index must be non-negative")
    
    return errors


def validate_trade_input(trade: TradeInput, limits: TradeLimits) -> List[str]:
    """
    Validate trade input against contract limits.
    
    Args:
        trade: Trade input to validate
        limits: Contract limits
    
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Position size validation
    if trade["initialPosToken"] <= 0:
        errors.append("Initial position token amount must be positive")
    elif trade["initialPosToken"] < limits["minPositionSize"]:
        errors.append(f"Position size {trade['initialPosToken']} below minimum {limits['minPositionSize']}")
    elif trade["initialPosToken"] > limits["maxPositionSize"]:
        errors.append(f"Position size {trade['initialPosToken']} above maximum {limits['maxPositionSize']}")
    
    # Leverage validation
    if trade["leverage"] <= 0:
        errors.append("Leverage must be positive")
    elif trade["leverage"] > limits["maxLeverage"]:
        errors.append(f"Leverage {trade['leverage']} above maximum {limits['maxLeverage']}")
    
    # Pair index validation
    if trade["pairIndex"] < 0:
        errors.append("Pair index must be non-negative")
    elif trade["pairIndex"] >= limits["maxPairs"]:
        errors.append(f"Pair index {trade['pairIndex']} exceeds maximum {limits['maxPairs'] - 1}")
    
    # Market order validation
    if trade["openPrice"] != 0:
        if trade["openPrice"] <= 0:
            errors.append("Limit order price must be positive")
    
    return errors


def validate_risk_limits(
    params: HumanTradeParams,
    risk_limits: RiskLimits,
    current_balance: Decimal
) -> List[str]:
    """
    Validate trade against risk management limits.
    
    Args:
        params: Human trade parameters
        risk_limits: Risk management limits
        current_balance: Current account balance
    
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Position size risk
    position_size_usd = params.collateral_usdc * params.leverage_x
    if position_size_usd > risk_limits.max_position_size_usd:
        errors.append(
            f"Position size ${position_size_usd:,.2f} exceeds maximum ${risk_limits.max_position_size_usd:,.2f}"
        )
    
    # Account risk validation
    account_risk_pct = (params.collateral_usdc / current_balance) * Decimal("100")
    if account_risk_pct > risk_limits.max_account_risk_pct * Decimal("100"):
        errors.append(
            f"Account risk {account_risk_pct:.2f}% exceeds maximum {risk_limits.max_account_risk_pct * Decimal('100'):.2f}%"
        )
    
    return errors


def clamp_trade_params(
    params: HumanTradeParams,
    limits: TradeLimits,
    risk_limits: RiskLimits,
    current_balance: Decimal
) -> HumanTradeParams:
    """
    Clamp trade parameters to safe limits.
    
    Args:
        params: Original trade parameters
        limits: Contract limits
        risk_limits: Risk management limits
        current_balance: Current account balance
    
    Returns:
        Clamped trade parameters within safe limits
    """
    # Clamp collateral
    collateral_min = Decimal("1")
    collateral_max = min(
        Decimal("100000"),
        risk_limits.max_position_size_usd / params.leverage_x,
        current_balance * risk_limits.max_account_risk_pct
    )
    collateral_clamped = max(collateral_min, min(params.collateral_usdc, collateral_max))
    
    # Clamp leverage
    leverage_min = Decimal("1")
    leverage_max = min(
        Decimal("500"),
        Decimal(limits["maxLeverage"]) / Decimal(10**10),  # Convert from 1e10 scale
        risk_limits.max_position_size_usd / collateral_clamped
    )
    leverage_clamped = max(leverage_min, min(params.leverage_x, leverage_max))
    
    # Clamp slippage
    slippage_clamped = max(Decimal("0"), min(params.slippage_pct, Decimal("10")))
    
    return HumanTradeParams(
        collateral_usdc=collateral_clamped,
        leverage_x=leverage_clamped,
        slippage_pct=slippage_clamped,
        pair_index=params.pair_index,
        is_long=params.is_long,
        order_type=params.order_type
    )


def validate_scaling_consistency(trade_units: TradeUnits) -> bool:
    """
    Validate that scaling is consistent and no double-scaling occurred.
    
    Args:
        trade_units: Scaled trade parameters
    
    Returns:
        True if scaling is consistent, False otherwise
    """
    # Check for obvious double-scaling indicators
    # If leverage is > 10^15, it's likely double-scaled
    if trade_units.leverage > 10**15:
        logger.error(f"Suspected double-scaling: leverage {trade_units.leverage} > 10^15")
        return False
    
    # If slippage is > 10^15, it's likely double-scaled
    if trade_units.slippage > 10**15:
        logger.error(f"Suspected double-scaling: slippage {trade_units.slippage} > 10^15")
        return False
    
    # Check position size consistency
    expected_position_size = (trade_units.initial_pos_token * trade_units.leverage) // (10**10)
    if trade_units.position_size_usdc != expected_position_size:
        logger.error(
            f"Position size inconsistency: expected {expected_position_size}, "
            f"got {trade_units.position_size_usdc}"
        )
        return False
    
    return True


def validate_market_order_invariant(trade: TradeInput) -> bool:
    """
    Validate that market orders have openPrice = 0.
    
    Args:
        trade: Trade input to validate
    
    Returns:
        True if invariant holds, False otherwise
    """
    # For market orders, openPrice should always be 0
    if trade["openPrice"] != 0:
        logger.error(f"Market order invariant violation: openPrice {trade['openPrice']} != 0")
        return False
    
    return True


def comprehensive_validation(
    params: HumanTradeParams,
    limits: TradeLimits,
    risk_limits: RiskLimits,
    current_balance: Decimal
) -> tuple[bool, List[str], Optional[HumanTradeParams]]:
    """
    Perform comprehensive validation and clamping of trade parameters.
    
    Args:
        params: Human trade parameters
        limits: Contract limits
        risk_limits: Risk management limits
        current_balance: Current account balance
    
    Returns:
        Tuple of (is_valid, errors, clamped_params)
    """
    # Initial validation
    errors = validate_human_trade_params(params)
    if errors:
        return False, errors, None
    
    # Risk validation
    risk_errors = validate_risk_limits(params, risk_limits, current_balance)
    if risk_errors:
        return False, risk_errors, None
    
    # Clamp parameters to safe limits
    clamped_params = clamp_trade_params(params, limits, risk_limits, current_balance)
    
    # Validate clamped parameters
    clamped_errors = validate_human_trade_params(clamped_params)
    if clamped_errors:
        return False, clamped_errors, None
    
    # Convert to trade units and validate scaling
    try:
        trade_units = to_trade_units(
            clamped_params.collateral_usdc,
            clamped_params.leverage_x,
            clamped_params.slippage_pct
        )
        
        if not validate_scaling_consistency(trade_units):
            return False, ["Scaling consistency validation failed"], None
            
    except ValueError as e:
        return False, [str(e)], None
    
    return True, [], clamped_params
