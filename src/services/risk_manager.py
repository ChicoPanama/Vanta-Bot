"""
Leverage Safety Manager
Critical risk management for 500x leveraged trading on Avantis Protocol
"""

from decimal import Decimal
from dataclasses import dataclass
from typing import Optional, Dict, Any
import logging
import os

from src.config.settings import settings

log = logging.getLogger(__name__)


@dataclass
class RiskLimits:
    max_position_size_usd: Decimal = Decimal('100000')  # $100k max
    max_account_risk_pct: Decimal = Decimal('0.10')     # 10% max account risk
    max_leverage: Decimal = Decimal('500')
    liquidation_buffer_pct: Decimal = Decimal('0.05')   # 5% buffer before liquidation
    max_daily_loss_pct: Decimal = Decimal('0.20')       # 20% daily loss limit


class RiskError(Exception):
    """Raised when risk limits are exceeded"""
    pass


class LeverageSafetyManager:
    def __init__(self, risk_limits: Optional[RiskLimits] = None):
        self.limits = risk_limits or self._load_limits_from_config()
    
    def _load_limits_from_config(self) -> RiskLimits:
        """Load risk limits from environment configuration"""
        return RiskLimits(
            max_position_size_usd=Decimal(str(os.getenv('MAX_POSITION_SIZE_USD', '100000'))),
            max_account_risk_pct=Decimal(str(os.getenv('MAX_ACCOUNT_RISK_PCT', '0.10'))),
            max_leverage=Decimal(str(os.getenv('MAX_LEVERAGE', '500'))),
            liquidation_buffer_pct=Decimal(str(os.getenv('LIQUIDATION_BUFFER_PCT', '0.05'))),
            max_daily_loss_pct=Decimal(str(os.getenv('MAX_DAILY_LOSS_PCT', '0.20')))
        )
    
    def validate_position(
        self, 
        position_size_usd: Decimal, 
        leverage: Decimal, 
        account_balance: Decimal,
        current_daily_pnl: Decimal = Decimal('0')
    ) -> Dict[str, Any]:
        """Validate position against risk limits. Returns risk metrics."""
        
        # Check position size limit
        if position_size_usd > self.limits.max_position_size_usd:
            raise RiskError(f"Position size ${position_size_usd} exceeds limit ${self.limits.max_position_size_usd}")
        
        # Check leverage limit
        if leverage > self.limits.max_leverage:
            raise RiskError(f"Leverage {leverage}x exceeds limit {self.limits.max_leverage}x")
        
        # Calculate margin required
        margin_required = position_size_usd / leverage
        
        # Check account balance
        if margin_required > account_balance:
            raise RiskError(f"Insufficient margin: need ${margin_required}, have ${account_balance}")
        
        # Calculate maximum loss with 2% adverse move (worst case scenario)
        max_loss_2pct = position_size_usd * Decimal('0.02')
        account_risk_pct = max_loss_2pct / account_balance
        
        if account_risk_pct > self.limits.max_account_risk_pct:
            raise RiskError(
                f"Position risk {account_risk_pct:.1%} exceeds limit {self.limits.max_account_risk_pct:.1%}"
            )
        
        # Check liquidation distance
        liquidation_price_distance = Decimal('1') / leverage  # 1/leverage = liquidation distance
        if liquidation_price_distance < self.limits.liquidation_buffer_pct:
            log.warning(
                "High liquidation risk: %s%% distance to liquidation", 
                liquidation_price_distance * 100
            )
        
        # Check daily loss limits
        potential_daily_loss = current_daily_pnl + max_loss_2pct
        daily_loss_pct = abs(potential_daily_loss) / account_balance
        
        if daily_loss_pct > self.limits.max_daily_loss_pct:
            raise RiskError(
                f"Potential daily loss {daily_loss_pct:.1%} exceeds limit {self.limits.max_daily_loss_pct:.1%}"
            )
        
        return {
            'margin_required': margin_required,
            'account_risk_pct': account_risk_pct,
            'liquidation_distance_pct': liquidation_price_distance,
            'max_loss_2pct': max_loss_2pct,
            'risk_score': min(1.0, float(account_risk_pct / self.limits.max_account_risk_pct))
        }
    
    def calculate_max_position_size(self, account_balance: Decimal, leverage: Decimal) -> Decimal:
        """Calculate maximum safe position size given account balance and leverage."""
        max_loss_allowed = account_balance * self.limits.max_account_risk_pct
        # If 2% adverse move causes max_loss_allowed, what's the position size?
        max_position = max_loss_allowed / Decimal('0.02')
        
        # Also respect absolute position limit
        return min(max_position, self.limits.max_position_size_usd)
    
    def calculate_safe_leverage(self, account_balance: Decimal, position_size_usd: Decimal) -> Decimal:
        """Calculate maximum safe leverage for a given position size."""
        max_loss_allowed = account_balance * self.limits.max_account_risk_pct
        max_position_for_2pct_loss = max_loss_allowed / Decimal('0.02')
        
        if position_size_usd > max_position_for_2pct_loss:
            return Decimal('1')  # Force 1x leverage if position too large
        
        # Calculate leverage that keeps 2% move within risk limits
        safe_leverage = position_size_usd / account_balance
        return min(safe_leverage, self.limits.max_leverage)
    
    def get_risk_summary(self, account_balance: Decimal) -> Dict[str, Any]:
        """Get risk management summary for account."""
        return {
            'limits': {
                'max_position_size_usd': float(self.limits.max_position_size_usd),
                'max_account_risk_pct': float(self.limits.max_account_risk_pct),
                'max_leverage': float(self.limits.max_leverage),
                'liquidation_buffer_pct': float(self.limits.liquidation_buffer_pct),
                'max_daily_loss_pct': float(self.limits.max_daily_loss_pct)
            },
            'account_balance_usd': float(account_balance),
            'max_safe_position_1x': float(account_balance),
            'max_safe_position_10x': float(self.calculate_max_position_size(account_balance, Decimal('10'))),
            'max_safe_position_100x': float(self.calculate_max_position_size(account_balance, Decimal('100'))),
            'max_safe_position_500x': float(self.calculate_max_position_size(account_balance, Decimal('500')))
        }


# Global risk manager instance
risk_manager = LeverageSafetyManager()
