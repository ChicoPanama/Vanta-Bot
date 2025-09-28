"""Base oracle interfaces and protocols for price feeds."""

from dataclasses import dataclass
from typing import Protocol, Optional
from decimal import Decimal


@dataclass
class Price:
    """Price data with metadata for validation."""
    symbol: str
    price: int  # 1e8 fixed-point
    conf: int   # confidence interval (1e8 scale)
    ts: int     # unix seconds
    source: str


class Oracle(Protocol):
    """Oracle interface for price feeds."""
    
    async def get_price(self, symbol: str, max_age_s: int = 5, max_dev_bps: int = 50) -> Price:
        """Get price for symbol with validation.
        
        Args:
            symbol: Market symbol (e.g., 'BTC', 'ETH')
            max_age_s: Maximum age in seconds
            max_dev_bps: Maximum deviation in basis points
            
        Returns:
            Price object with validation metadata
            
        Raises:
            ValueError: If price is stale, invalid, or deviation too high
        """
        ...
