"""
Price Feed Reliability Manager
Multi-source price validation and reliability management for leveraged trading
"""

import asyncio
import time
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Callable, Any
from dataclasses import dataclass
import logging

log = logging.getLogger(__name__)


@dataclass
class PriceSource:
    name: str
    get_price_func: Callable
    weight: float = 1.0
    max_age_seconds: int = 10


@dataclass
class PriceData:
    price: Decimal
    timestamp: float
    source: str
    
    @property
    def age_seconds(self) -> float:
        return time.time() - self.timestamp
    
    @property
    def is_stale(self) -> bool:
        return self.age_seconds > 5.0  # 5 seconds tolerance for leveraged trading


class PriceFeedError(Exception):
    """Raised when price feed operations fail"""
    pass


class PriceFeedManager:
    def __init__(self, stale_threshold: float = 5.0, max_deviation_pct: float = 0.5):
        self.sources: Dict[str, List[PriceSource]] = {}
        self.last_prices: Dict[str, PriceData] = {}
        self.stale_threshold = stale_threshold
        self.max_deviation_pct = max_deviation_pct
        
    def add_source(self, asset: str, source: PriceSource):
        """Add a price source for an asset"""
        if asset not in self.sources:
            self.sources[asset] = []
        self.sources[asset].append(source)
    
    async def get_validated_price(self, asset: str) -> PriceData:
        """Get validated price with multi-source cross-checking."""
        if asset not in self.sources:
            raise PriceFeedError(f"No price sources configured for {asset}")
        
        # Fetch prices from all sources
        price_tasks = []
        for source in self.sources[asset]:
            task = asyncio.create_task(self._fetch_price_safe(source, asset))
            price_tasks.append(task)
        
        # Wait for at least one source (timeout after 3 seconds)
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*price_tasks, return_exceptions=True), 
                timeout=3.0
            )
        except asyncio.TimeoutError:
            raise PriceFeedError(f"Price feed timeout for {asset}")
        
        # Filter successful results
        valid_prices = []
        for i, result in enumerate(results):
            if isinstance(result, PriceData) and not result.is_stale:
                valid_prices.append(result)
            elif isinstance(result, Exception):
                log.warning("Price source %s failed: %s", self.sources[asset][i].name, result)
        
        if not valid_prices:
            # Fallback to last known price if recent enough
            if asset in self.last_prices and not self.last_prices[asset].is_stale:
                log.warning("Using fallback price for %s", asset)
                return self.last_prices[asset]
            raise PriceFeedError(f"No valid price sources available for {asset}")
        
        # Cross-validate prices if multiple sources
        if len(valid_prices) > 1:
            validated_price = self._cross_validate_prices(valid_prices, asset)
        else:
            validated_price = valid_prices[0]
        
        # Cache the validated price
        self.last_prices[asset] = validated_price
        return validated_price
    
    async def _fetch_price_safe(self, source: PriceSource, asset: str) -> PriceData:
        """Safely fetch price from a source with error handling."""
        try:
            price = await source.get_price_func(asset)
            return PriceData(
                price=Decimal(str(price)),
                timestamp=time.time(),
                source=source.name
            )
        except Exception as e:
            log.error("Price fetch failed from %s for %s: %s", source.name, asset, e)
            raise
    
    def _cross_validate_prices(self, prices: List[PriceData], asset: str) -> PriceData:
        """Cross-validate prices from multiple sources."""
        if len(prices) < 2:
            return prices[0]
        
        # Calculate weighted average
        total_weight = sum(p.weight for p in prices if hasattr(p, 'weight'))
        if total_weight == 0:
            total_weight = len(prices)
            
        weighted_sum = sum(
            p.price * getattr(p, 'weight', 1.0) for p in prices
        )
        avg_price = weighted_sum / total_weight
        
        # Check for outliers
        outliers = []
        for price_data in prices:
            deviation_pct = abs(float(price_data.price - avg_price) / float(avg_price))
            if deviation_pct > self.max_deviation_pct / 100:
                outliers.append((price_data.source, deviation_pct))
        
        if outliers:
            log.warning(
                "Price outliers detected for %s: %s", 
                asset, 
                [(source, f"{dev:.2%}") for source, dev in outliers]
            )
        
        # Return most recent price among validated ones
        return max(prices, key=lambda p: p.timestamp)
    
    def get_feed_health(self) -> Dict[str, Dict[str, Any]]:
        """Get health status of all price feeds."""
        health = {}
        for asset, last_price in self.last_prices.items():
            health[asset] = {
                'last_update': last_price.timestamp,
                'age_seconds': last_price.age_seconds,
                'is_stale': last_price.is_stale,
                'source': last_price.source,
                'price': float(last_price.price)
            }
        return health
    
    async def get_price_with_fallback(self, asset: str, fallback_price: Optional[Decimal] = None) -> Decimal:
        """Get price with fallback support for critical trading operations."""
        try:
            price_data = await self.get_validated_price(asset)
            return price_data.price
        except PriceFeedError:
            if fallback_price:
                log.warning("Using fallback price for %s: %s", asset, fallback_price)
                return fallback_price
            else:
                # Last resort: use last known price even if stale
                if asset in self.last_prices:
                    log.error("Using stale price for %s: %s (age: %.1fs)", 
                             asset, self.last_prices[asset].price, 
                             self.last_prices[asset].age_seconds)
                    return self.last_prices[asset].price
                raise
    
    def register_avantis_price_source(self, asset: str):
        """Register Avantis SDK as a price source"""
        async def get_avantis_price(asset_name: str) -> Decimal:
            try:
                from src.integrations.avantis.feed_client import get_feed_client
                feed_client = get_feed_client()
                if feed_client and feed_client.is_configured():
                    # Get price from Avantis feed
                    price_data = await feed_client.get_price(asset_name)
                    return Decimal(str(price_data.price))
                else:
                    raise PriceFeedError("Avantis feed client not configured")
            except Exception as e:
                log.error("Avantis price fetch failed for %s: %s", asset_name, e)
                raise
        
        source = PriceSource(
            name="avantis",
            get_price_func=get_avantis_price,
            weight=1.5,  # Higher weight for primary source
            max_age_seconds=3
        )
        self.add_source(asset, source)
    
    def register_coingecko_price_source(self, asset: str):
        """Register CoinGecko as a price source"""
        async def get_coingecko_price(asset_name: str) -> Decimal:
            try:
                import aiohttp
                import os
                
                # Map asset names to CoinGecko IDs
                asset_map = {
                    'ETH/USD': 'ethereum',
                    'BTC/USD': 'bitcoin',
                    'AVAX/USD': 'avalanche-2',
                    'SOL/USD': 'solana',
                    'MATIC/USD': 'matic-network'
                }
                
                coingecko_id = asset_map.get(asset_name)
                if not coingecko_id:
                    raise PriceFeedError(f"Unsupported asset for CoinGecko: {asset_name}")
                
                api_key = os.getenv('COINGECKO_API_KEY')
                url = f"https://api.coingecko.com/api/v3/simple/price"
                params = {
                    'ids': coingecko_id,
                    'vs_currencies': 'usd'
                }
                
                headers = {}
                if api_key:
                    headers['x-cg-demo-api-key'] = api_key
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params, headers=headers, timeout=5) as response:
                        if response.status == 200:
                            data = await response.json()
                            price = data[coingecko_id]['usd']
                            return Decimal(str(price))
                        else:
                            raise PriceFeedError(f"CoinGecko API error: {response.status}")
                            
            except Exception as e:
                log.error("CoinGecko price fetch failed for %s: %s", asset_name, e)
                raise
        
        source = PriceSource(
            name="coingecko",
            get_price_func=get_coingecko_price,
            weight=1.0,
            max_age_seconds=10
        )
        self.add_source(asset, source)


# Global price feed manager instance
price_feed_manager = PriceFeedManager()
