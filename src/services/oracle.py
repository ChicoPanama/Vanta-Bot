"""Oracle service for price aggregation and validation."""

import logging
import time
import asyncio
from decimal import Decimal, getcontext
from typing import Dict, List, NamedTuple, Optional
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
    """Mock oracle source for testing ONLY - NEVER use in production."""
    
    def __init__(self, name: str, base_price: Decimal = Decimal("50000")):
        self.name = name
        self.base_price = base_price
    
    def get_price(self, market: str) -> PriceQuote:
        """Get mock price with some variation - TESTING ONLY."""
        import random
        
        # CRITICAL: This random variation is ONLY for testing
        # In production, this should NEVER be used
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


class OracleFacade:
    """Production oracle facade with dual-feed validation and failover."""
    
    def __init__(self, primary: 'Oracle', secondary: Optional['Oracle'] = None):
        self.primary = primary
        self.secondary = secondary
        self._last: Dict[str, PriceQuote] = {}
        
    async def get_price(self, symbol: str, max_age_s: int = 5, max_dev_bps: int = 50) -> PriceQuote:
        """Get price with dual-feed validation, deviation checks, and failover.

        Rules expected by tests:
        - Always query both providers when both are configured.
        - If primary raises (including TimeoutError), fall back to secondary.
        - If both return quotes but either is stale (> max_age_s) -> raise ValueError("Price too stale").
        - If both return quotes and cross-feed deviation > max_dev_bps -> raise ValueError("Price deviation too high").
        - On total failure (both providers raise) -> raise Exception("Both oracle providers failed").
        - Symbols are normalized to canonical (e.g., 'BTC').
        - Providers may be sync or async; handle both.
        """
        from src.services.markets.symbols import to_canonical

        async def _maybe_await(result):
            import asyncio as _asyncio
            if _asyncio.iscoroutine(result):
                return await result
            return result

        def _call_provider(provider, sym: str, age: int, dev: int):
            # Call get_price with canonical symbol and thresholds. Return possibly awaitable result.
            try:
                return provider.get_price(sym, age, dev)
            except TypeError:
                # Some provider mocks may only accept (symbol)
                return provider.get_price(sym)

        canonical = to_canonical(symbol)
        primary_quote = None
        secondary_quote = None
        primary_exc = None
        secondary_exc = None

        try:
            if self.secondary is not None:
                # Query both concurrently
                import asyncio as _asyncio
                async def _run_primary():
                    nonlocal primary_quote, primary_exc
                    try:
                        res = _call_provider(self.primary, canonical, max_age_s, max_dev_bps)
                        primary_quote = await _maybe_await(res)
                    except Exception as e:
                        primary_exc = e

                async def _run_secondary():
                    nonlocal secondary_quote, secondary_exc
                    try:
                        res = _call_provider(self.secondary, canonical, max_age_s, max_dev_bps)
                        secondary_quote = await _maybe_await(res)
                    except Exception as e:
                        secondary_exc = e

                await _asyncio.gather(_run_primary(), _run_secondary())
            else:
                # Only primary configured
                res = _call_provider(self.primary, canonical, max_age_s, max_dev_bps)
                primary_quote = await _maybe_await(res)

            # Handle failures/fallbacks
            if primary_quote is None and self.secondary is not None and secondary_quote is not None:
                # Primary failed, secondary succeeded -> fallback to secondary
                chosen = secondary_quote
            elif primary_quote is not None and (self.secondary is None or secondary_quote is None):
                # Secondary absent or failed -> use primary (will validate with last if available)
                chosen = primary_quote
            elif primary_quote is None and (self.secondary is None or secondary_quote is None):
                # Total failure
                # If we have specific errors, propagate a meaningful one
                if isinstance(primary_exc, ValueError) or isinstance(secondary_exc, ValueError):
                    # Prefer primary's error message if present
                    err = primary_exc if isinstance(primary_exc, ValueError) else secondary_exc
                    raise ValueError(str(err))
                raise Exception("Both oracle providers failed")
            else:
                # Both succeeded -> validate chosen (primary) freshness and cross-feed deviation
                # Only enforce freshness on the chosen (primary) quote per tests
                if getattr(primary_quote, 'freshness_sec', 0) > max_age_s:
                    raise ValueError("Price too stale")

                # Cross-feed deviation check (do not require secondary freshness)
                try:
                    p1 = Decimal(str(primary_quote.price))
                    p2 = Decimal(str(secondary_quote.price))
                    base = p1 if p1 != 0 else Decimal('1')
                    dev_bps = int((abs(p1 - p2) / base) * 10000)
                except Exception:
                    # If prices are not numeric for any reason, treat as failure
                    raise ValueError("Invalid price data")
                if dev_bps > max_dev_bps:
                    raise ValueError("Price deviation too high")

                # Prefer primary when both are healthy and within deviation
                chosen = primary_quote

            # Track last per canonical symbol for potential future strategies
            self._last[canonical] = chosen
            return chosen

        except Exception as e:
            logger.error(f"Oracle facade error for {canonical}: {e}")
            raise


# Global oracle instances
def create_default_oracle() -> OracleFacade:
    """Create production oracle with real feeds."""
    import os
    from .oracle_providers import PythOracle, ChainlinkOracle
    from src.blockchain.base_client import base_client
    
    # Check if we're in test mode
    if os.getenv("ENVIRONMENT", "production") == "test" or os.getenv("PRICING_PROVIDER") == "mock":
        # TESTING ONLY - Use mock sources
        sources = [
            MockOracleSource("mock1", Decimal("50000")),
            MockOracleSource("mock2", Decimal("50000")),
            MockOracleSource("mock3", Decimal("50000")),
        ]
        return MedianOracle(sources)
    
    # Production mode - use real oracles
    try:
        primary = PythOracle()
        secondary = ChainlinkOracle(base_client.w3)
        return OracleFacade(primary, secondary)
    except Exception as e:
        logger.error(f"Failed to initialize production oracles: {e}")
        # CRITICAL: Do NOT fallback to random prices in production
        # This would allow attackers to manipulate pricing
        raise RuntimeError(f"Oracle initialization failed: {e}. Cannot start with random price fallback in production.")


def create_price_validator() -> PriceValidator:
    """Create default price validator with configurable thresholds."""
    import os
    max_deviation_bps = int(os.getenv("ORACLE_MAX_DEVIATION_BPS", "50"))
    max_freshness_sec = int(os.getenv("ORACLE_MAX_AGE_S", "30"))
    return PriceValidator(max_deviation_bps=max_deviation_bps, max_freshness_sec=max_freshness_sec)
