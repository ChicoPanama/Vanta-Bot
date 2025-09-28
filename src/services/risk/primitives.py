"""Financial primitives for risk calculations."""

from decimal import Decimal, getcontext
from typing import NamedTuple, Optional
import logging

# Set high precision for financial calculations
getcontext().prec = 50

logger = logging.getLogger(__name__)


class PositionInfo(NamedTuple):
    """Position information for risk calculations."""
    entry_price: Decimal
    current_price: Decimal
    size: Decimal
    leverage: Decimal
    side: str  # 'long' or 'short'
    fee_rate: Decimal = Decimal('0.001')  # 0.1% default fee
    maintenance_margin: Decimal = Decimal('0.05')  # 5% maintenance margin


class RiskMetrics(NamedTuple):
    """Risk metrics for a position."""
    pnl: Decimal
    pnl_percentage: Decimal
    liquidation_price: Decimal
    margin_ratio: Decimal
    risk_score: Decimal


def calculate_pnl(entry_price: Decimal, current_price: Decimal, size: Decimal, side: str) -> Decimal:
    """Calculate profit and loss for a position.
    
    Args:
        entry_price: Entry price of the position
        current_price: Current market price
        size: Position size in base currency
        side: 'long' or 'short'
        
    Returns:
        PnL in quote currency
    """
    if side == 'long':
        return (current_price - entry_price) / entry_price * size
    elif side == 'short':
        return (entry_price - current_price) / entry_price * size
    else:
        raise ValueError(f"Invalid side: {side}. Must be 'long' or 'short'")


def calculate_liquidation_price(entry_price: Decimal, leverage: Decimal, fee_rate: Decimal, 
                                maintenance_margin: Decimal, side: str) -> Decimal:
    """Calculate liquidation price for a position.
    
    Args:
        entry_price: Entry price of the position
        leverage: Leverage multiplier
        fee_rate: Fee rate (e.g., 0.001 for 0.1%)
        maintenance_margin: Maintenance margin requirement
        side: 'long' or 'short'
        
    Returns:
        Liquidation price
    """
    # Total margin requirement including fees
    total_margin = maintenance_margin + fee_rate
    
    if side == 'long':
        # For long positions: liquidation when price drops below threshold
        return entry_price * (Decimal('1') - (Decimal('1') / leverage) + total_margin)
    elif side == 'short':
        # For short positions: liquidation when price rises above threshold
        return entry_price * (Decimal('1') + (Decimal('1') / leverage) - total_margin)
    else:
        raise ValueError(f"Invalid side: {side}. Must be 'long' or 'short'")


def calculate_margin_ratio(entry_price: Decimal, current_price: Decimal, leverage: Decimal, 
                           side: str) -> Decimal:
    """Calculate current margin ratio.
    
    Args:
        entry_price: Entry price of the position
        current_price: Current market price
        leverage: Leverage multiplier
        side: 'long' or 'short'
        
    Returns:
        Current margin ratio
    """
    if side == 'long':
        # For long positions: margin decreases as price drops
        return Decimal('1') - (entry_price - current_price) / entry_price * leverage
    elif side == 'short':
        # For short positions: margin decreases as price rises
        return Decimal('1') - (current_price - entry_price) / entry_price * leverage
    else:
        raise ValueError(f"Invalid side: {side}. Must be 'long' or 'short'")


def calculate_risk_score(position: PositionInfo) -> Decimal:
    """Calculate risk score for a position.
    
    Args:
        position: Position information
        
    Returns:
        Risk score (0-1, where 1 is highest risk)
    """
    try:
        # Calculate current PnL
        pnl = calculate_pnl(
            position.entry_price,
            position.current_price,
            position.size,
            position.side
        )
        
        # Calculate liquidation price
        liquidation_price = calculate_liquidation_price(
            position.entry_price,
            position.leverage,
            position.fee_rate,
            position.maintenance_margin,
            position.side
        )
        
        # Calculate margin ratio
        margin_ratio = calculate_margin_ratio(
            position.entry_price,
            position.current_price,
            position.leverage,
            position.side
        )
        
        # Risk factors
        leverage_risk = min(position.leverage / Decimal('10'), Decimal('1'))  # Higher leverage = higher risk
        
        # Distance to liquidation (0-1, where 1 is at liquidation)
        if position.side == 'long':
            liquidation_distance = max(Decimal('0'), 
                (position.current_price - liquidation_price) / position.current_price)
        else:
            liquidation_distance = max(Decimal('0'),
                (liquidation_price - position.current_price) / position.current_price)
        
        # Margin ratio risk (0-1, where 1 is at maintenance margin)
        margin_risk = max(Decimal('0'), 
            (Decimal('1') - margin_ratio) / (Decimal('1') - position.maintenance_margin))
        
        # Combined risk score (weighted average)
        risk_score = (
            leverage_risk * Decimal('0.3') +
            liquidation_distance * Decimal('0.4') +
            margin_risk * Decimal('0.3')
        )
        
        return min(risk_score, Decimal('1'))  # Cap at 1
        
    except Exception as e:
        logger.error(f"Failed to calculate risk score: {e}")
        return Decimal('1')  # Return maximum risk on error


def calculate_position_metrics(position: PositionInfo) -> RiskMetrics:
    """Calculate comprehensive risk metrics for a position.
    
    Args:
        position: Position information
        
    Returns:
        Risk metrics
    """
    try:
        # Calculate PnL
        pnl = calculate_pnl(
            position.entry_price,
            position.current_price,
            position.size,
            position.side
        )
        
        # Calculate PnL percentage
        pnl_percentage = pnl / position.size * Decimal('100')
        
        # Calculate liquidation price
        liquidation_price = calculate_liquidation_price(
            position.entry_price,
            position.leverage,
            position.fee_rate,
            position.maintenance_margin,
            position.side
        )
        
        # Calculate margin ratio
        margin_ratio = calculate_margin_ratio(
            position.entry_price,
            position.current_price,
            position.leverage,
            position.side
        )
        
        # Calculate risk score
        risk_score = calculate_risk_score(position)
        
        return RiskMetrics(
            pnl=pnl,
            pnl_percentage=pnl_percentage,
            liquidation_price=liquidation_price,
            margin_ratio=margin_ratio,
            risk_score=risk_score
        )
        
    except Exception as e:
        logger.error(f"Failed to calculate position metrics: {e}")
        raise


def validate_position_size(size: Decimal, min_size: Decimal, max_size: Decimal) -> bool:
    """Validate position size against limits.
    
    Args:
        size: Position size to validate
        min_size: Minimum allowed size
        max_size: Maximum allowed size
        
    Returns:
        True if valid, False otherwise
    """
    return min_size <= size <= max_size


def validate_leverage(leverage: Decimal, max_leverage: Decimal) -> bool:
    """Validate leverage against limits.
    
    Args:
        leverage: Leverage to validate
        max_leverage: Maximum allowed leverage
        
    Returns:
        True if valid, False otherwise
    """
    return Decimal('1') <= leverage <= max_leverage


def calculate_portfolio_risk(positions: list[PositionInfo]) -> Decimal:
    """Calculate portfolio-level risk.
    
    Args:
        positions: List of position information
        
    Returns:
        Portfolio risk score (0-1)
    """
    if not positions:
        return Decimal('0')
    
    try:
        # Calculate individual position risks
        position_risks = []
        total_exposure = Decimal('0')
        
        for position in positions:
            metrics = calculate_position_metrics(position)
            position_risks.append(metrics.risk_score)
            total_exposure += position.size * position.leverage
        
        # Weight by position size
        weighted_risk = Decimal('0')
        for i, risk in enumerate(position_risks):
            weight = positions[i].size * positions[i].leverage / total_exposure
            weighted_risk += risk * weight
        
        # Add concentration risk (more positions = lower risk)
        concentration_factor = Decimal('1') - min(Decimal(len(positions)) / Decimal('10'), Decimal('0.5'))
        
        portfolio_risk = weighted_risk * (Decimal('1') - concentration_factor)
        
        return min(portfolio_risk, Decimal('1'))
        
    except Exception as e:
        logger.error(f"Failed to calculate portfolio risk: {e}")
        return Decimal('1')  # Return maximum risk on error
