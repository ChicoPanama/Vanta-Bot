"""
Authoritative mathematical calculations for Avantis trading.

This module provides the single source of truth for all scaling operations,
ensuring consistent parameter conversion across the entire application.

Key invariants:
- USDC has 6 decimal places
- Leverage and slippage use 1e10 scaling
- All calculations use Decimal for precision
- Single scaling only - no double scaling allowed
"""

from decimal import Decimal
from typing import Tuple, NamedTuple


# Scaling constants - single source of truth
USDC_6 = Decimal(10) ** 6      # USDC has 6 decimal places
SCALE_1E10 = Decimal(10) ** 10  # Leverage and slippage scaling


class TradeUnits(NamedTuple):
    """Scaled trade parameters ready for contract interaction."""
    initial_pos_token: int      # USDC collateral in 6dp
    leverage: int              # Leverage in 1e10 scale
    position_size_usdc: int    # Position size in 6dp
    slippage: int              # Slippage in 1e10 scale (e.g., 100_000_000 = 1%)


def to_trade_units(
    collateral_usdc: Decimal,
    leverage_x: Decimal,
    slippage_pct: Decimal
) -> TradeUnits:
    """
    Convert human-readable trading parameters to contract units.
    
    This is the authoritative scaling function - all other scaling
    operations in the codebase should use this function.
    
    Args:
        collateral_usdc: Collateral amount in USDC (e.g., 100.0 for $100)
        leverage_x: Leverage multiplier (e.g., 5.0 for 5x leverage)
        slippage_pct: Slippage percentage (e.g., 1.0 for 1% slippage)
    
    Returns:
        TradeUnits with all parameters properly scaled
        
    Raises:
        ValueError: If any parameter is invalid (negative, zero, etc.)
    """
    # Input validation
    if collateral_usdc <= 0:
        raise ValueError(f"Collateral must be positive, got {collateral_usdc}")
    if leverage_x <= 0:
        raise ValueError(f"Leverage must be positive, got {leverage_x}")
    if slippage_pct < 0:
        raise ValueError(f"Slippage cannot be negative, got {slippage_pct}")
    
    # Scale to contract units (single scaling)
    initial_pos_token = int(collateral_usdc * USDC_6)
    leverage_scaled = int(leverage_x * SCALE_1E10)
    position_size_usdc = (initial_pos_token * leverage_scaled) // int(SCALE_1E10)
    slippage_scaled = int((slippage_pct / Decimal(100)) * SCALE_1E10)
    
    return TradeUnits(
        initial_pos_token=initial_pos_token,
        leverage=leverage_scaled,
        position_size_usdc=position_size_usdc,
        slippage=slippage_scaled
    )


def from_trade_units(trade_units: TradeUnits) -> Tuple[Decimal, Decimal, Decimal]:
    """
    Convert contract units back to human-readable values.
    
    Args:
        trade_units: Scaled trade parameters from contract
    
    Returns:
        Tuple of (collateral_usdc, leverage_x, slippage_pct)
    """
    collateral_usdc = Decimal(trade_units.initial_pos_token) / USDC_6
    leverage_x = Decimal(trade_units.leverage) / SCALE_1E10
    slippage_pct = (Decimal(trade_units.slippage) / SCALE_1E10) * Decimal(100)
    
    return collateral_usdc, leverage_x, slippage_pct


def validate_scaling_invariant(trade_units: TradeUnits) -> bool:
    """
    Validate that the scaling invariant holds.
    
    The invariant: position_size_usdc should equal (initial_pos_token * leverage) / 1e10
    
    Args:
        trade_units: Trade parameters to validate
    
    Returns:
        True if invariant holds, False otherwise
    """
    expected_position_size = (trade_units.initial_pos_token * trade_units.leverage) // int(SCALE_1E10)
    return trade_units.position_size_usdc == expected_position_size


def get_max_safe_leverage(collateral_usdc: Decimal, max_position_usdc: Decimal) -> Decimal:
    """
    Calculate the maximum safe leverage for a given collateral amount.
    
    Args:
        collateral_usdc: Available collateral
        max_position_usdc: Maximum allowed position size
    
    Returns:
        Maximum safe leverage multiplier
    """
    if collateral_usdc <= 0:
        return Decimal(0)
    
    max_leverage = max_position_usdc / collateral_usdc
    return max_leverage


def calculate_liquidation_price(
    entry_price: Decimal,
    leverage: Decimal,
    is_long: bool
) -> Decimal:
    """
    Calculate liquidation price for a position.
    
    Args:
        entry_price: Entry price of the position
        leverage: Leverage multiplier
        is_long: True for long position, False for short
    
    Returns:
        Liquidation price
    """
    # Simplified liquidation calculation
    # In practice, this should use the actual protocol's liquidation formula
    if is_long:
        # Long position liquidates when price drops
        liquidation_price = entry_price * (Decimal(1) - Decimal(1) / leverage)
    else:
        # Short position liquidates when price rises
        liquidation_price = entry_price * (Decimal(1) + Decimal(1) / leverage)
    
    return liquidation_price
