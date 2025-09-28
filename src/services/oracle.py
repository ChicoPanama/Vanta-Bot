"""Oracle service for price aggregation and validation."""

import logging
import time
from decimal import Decimal, getcontext
from typing import Dict, List, NamedTuple
from statistics import median

# Set high precision for financial calculations
getcontext().prec = 50

logger = logging.getLogger(__name__)


class PriceQuote(NamedTuple):
    """Price quote with metadata."""
    price: Decimal
    timestamp: int
    source: str
    freshness_sec: int
    deviation_bps: int = 0


class OracleSource:
    """Base class for oracle price sources."""
    
    def get_price(self, market: str) -> PriceQuote:
        """Get price for market from this source."""
        raise NotImplementedError


class MockOracleSource(OracleSource):
    """Mock oracle source for testing."""
    
    def __init__(self, name: str, base_price: Decimal = Decimal("50000")):
        self.name = name
        self.base_price = base_price
    
    def get_price(self, market: str) -> PriceQuote:
        """Get mock price with some variation."""
        import random
        
        # Add some random variation
        variation = Decimal(str(random.uniform(-0.02, 0.02)))  # ±2%
        price = self.base_price * (Decimal("1") + variation)
        
        return PriceQuote(
            price=price,
            timestamp=int(time.time()),
            source=self.name,
            freshness_sec=0
        )


class MedianOracle:
    """Oracle that aggregates multiple price sources using median."""
    
    def __init__(self, sources: List[OracleSource], max_deviation_bps: int = 50):
        self.sources = sources
        self.max_deviation_bps = max_deviation_bps
        self.max_freshness_sec = 30  # 30 seconds max age

    def get_price(self, market: str) -> PriceQuote:
        """Get aggregated price for market.
        
        Args:
            market: Market symbol (e.g., 'BTC', 'ETH')
            
        Returns:
            Aggregated price quote
            
        Raises:
            ValueError: If no valid prices or deviation too high
        """
        try:
            # Get quotes from all sources
            quotes = []
            for source in self.sources:
                try:
                    quote = source.get_price(market)
                    quotes.append(quote)
                except Exception as e:
                    logger.warning(f"Source {source.__class__.__name__} failed for {market}: {e}")
                    continue
            
            if not quotes:
                raise ValueError(f"No valid price sources for {market}")
            
            # Filter by freshness
            now = int(time.time())
            fresh_quotes = [
                q for q in quotes 
                if (now - q.timestamp) <= self.max_freshness_sec
            ]
            
            if not fresh_quotes:
                raise ValueError(f"No fresh prices for {market} (max age: {self.max_freshness_sec}s)")
            
            # Calculate median price
            prices = [q.price for q in fresh_quotes]
            median_price = Decimal(str(median(prices)))
            
            # Calculate deviation from median
            max_deviation = Decimal("0")
            for price in prices:
                deviation = abs(price - median_price) / median_price
                max_deviation = max(max_deviation, deviation)
            
            deviation_bps = int(max_deviation * 10000)  # Convert to basis points
            
            # Check deviation threshold
            if deviation_bps > self.max_deviation_bps:
                raise ValueError(f"Price deviation too high: {deviation_bps}bps > {self.max_deviation_bps}bps")
            
            # Use most recent timestamp
            latest_timestamp = max(q.timestamp for q in fresh_quotes)
            freshness_sec = now - latest_timestamp
            
            return PriceQuote(
                price=median_price,
                timestamp=latest_timestamp,
                source="median",
                freshness_sec=freshness_sec,
                deviation_bps=deviation_bps
            )
            
        except Exception as e:
            logger.error(f"Failed to get price for {market}: {e}")
            raise

    def get_prices(self, markets: List[str]) -> Dict[str, PriceQuote]:
        """Get prices for multiple markets.
        
        Args:
            markets: List of market symbols
            
        Returns:
            Dict mapping market to price quote
        """
        results = {}
        for market in markets:
            try:
                results[market] = self.get_price(market)
            except Exception as e:
                logger.error(f"Failed to get price for {market}: {e}")
                # Continue with other markets
                continue
        
        return results


class PriceValidator:
    """Validates price quotes for trading safety."""
    
    def __init__(self, max_deviation_bps: int = 50, max_freshness_sec: int = 30):
        self.max_deviation_bps = max_deviation_bps
        self.max_freshness_sec = max_freshness_sec

    def validate_quote(self, quote: PriceQuote) -> bool:
        """Validate price quote for trading.
        
        Args:
            quote: Price quote to validate
            
        Returns:
            True if valid for trading
        """
        try:
            # Check freshness
            if quote.freshness_sec > self.max_freshness_sec:
                logger.warning(f"Price too stale: {quote.freshness_sec}s > {self.max_freshness_sec}s")
                return False
            
            # Check deviation
            if quote.deviation_bps > self.max_deviation_bps:
                logger.warning(f"Price deviation too high: {quote.deviation_bps}bps > {self.max_deviation_bps}bps")
                return False
            
            # Check price is positive
            if quote.price <= 0:
                logger.warning(f"Invalid price: {quote.price}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Price validation failed: {e}")
            return False

    def validate_prices(self, quotes: Dict[str, PriceQuote]) -> Dict[str, bool]:
        """Validate multiple price quotes.
        
        Args:
            quotes: Dict mapping market to price quote
            
        Returns:
            Dict mapping market to validation result
        """
        return {
            market: self.validate_quote(quote)
            for market, quote in quotes.items()
        }


# Global oracle instances
def create_default_oracle() -> MedianOracle:
    """Create default oracle with mock sources."""
    sources = [
        MockOracleSource("source1", Decimal("50000")),
        MockOracleSource("source2", Decimal("50000")),
        MockOracleSource("source3", Decimal("50000")),
    ]
    return MedianOracle(sources)


def create_price_validator() -> PriceValidator:
    """Create default price validator."""
    return PriceValidator(max_deviation_bps=50, max_freshness_sec=30)
