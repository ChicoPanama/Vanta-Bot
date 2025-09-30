"""Base price feed protocol (Phase 3)."""

from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass
class PriceQuote:
    """Price quote with metadata."""

    symbol: str  # e.g., "BTC-USD"
    price: int  # Integer-scaled price (e.g., 50000 * 1e8)
    decimals: int  # Scaling decimals (e.g., 8)
    source: str  # "pyth"|"chainlink"
    timestamp: int = 0  # Unix timestamp


class PriceFeed(Protocol):
    """Protocol for price feeds."""

    def get_price(self, symbol: str) -> Optional[PriceQuote]:
        """Get price for symbol.

        Args:
            symbol: Market symbol (e.g., "BTC-USD")

        Returns:
            PriceQuote or None if not available
        """
        ...
