"""Price aggregator with fallback strategy (Phase 3)."""

import logging
from typing import Optional

from .base import PriceFeed, PriceQuote

logger = logging.getLogger(__name__)


class PriceAggregator:
    """Aggregates multiple price feeds with fallback."""

    def __init__(self, feeds: list[PriceFeed]):
        """Initialize aggregator.

        Args:
            feeds: List of price feeds (tried in order)
        """
        self.feeds = feeds

    def get_price(self, symbol: str) -> Optional[PriceQuote]:
        """Get price from first available feed.

        Args:
            symbol: Market symbol

        Returns:
            PriceQuote from first successful feed or None
        """
        for feed in self.feeds:
            try:
                quote = feed.get_price(symbol)
                if quote is not None:
                    logger.debug(
                        f"Price for {symbol} from {quote.source}: {quote.price}"
                    )
                    return quote
            except Exception as e:
                logger.warning(
                    f"Feed {feed.__class__.__name__} failed for {symbol}: {e}"
                )
                continue

        logger.warning(f"No price available for {symbol} from any feed")
        return None
