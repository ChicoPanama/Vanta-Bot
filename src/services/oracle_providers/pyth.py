"""Pyth Network oracle provider for real-time price feeds."""

import logging
from typing import Optional

import aiohttp

from src.config.feeds_config import get_feeds_config
from src.services.markets.symbols import to_canonical

from ..oracle_base import Oracle, Price

logger = logging.getLogger(__name__)


class PythOracle(Oracle):
    """Pyth Network oracle implementation."""

    def __init__(self, api_url: str = None):
        if api_url is None:
            import os

            api_url = os.getenv(
                "PYTH_HERMES_ENDPOINT",
                "https://hermes.pyth.network/v2/updates/price/latest",
            )
        self.api_url = api_url

        # Prefer centralized feeds configuration; fallback to built-in defaults
        feeds_config = get_feeds_config()
        if feeds_config.is_available():
            self.symbol_map = feeds_config.get_pyth_symbols()
            if not self.symbol_map:
                self.symbol_map = {
                    "BTC": "0xe62df6c8b4a85fe1a67db44dc12de5db330f7ac66b4dc4e60a5713c7130b3bdf",
                    "ETH": "0xff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace",
                    "SOL": "0xef0d8b6fda2ceba41da15d4095d1da392a0d3f76cddcec9e8963b5f719819e4b",
                }
            logger.info(
                f"Loaded Pyth symbols from centralized config: {list(self.symbol_map.keys())}"
            )
        else:
            self.symbol_map = {
                "BTC": "0xe62df6c8b4a85fe1a67db44dc12de5db330f7ac66b4dc4e60a5713c7130b3bdf",
                "ETH": "0xff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace",
                "SOL": "0xef0d8b6fda2ceba41da15d4095d1da392a0d3f76cddcec9e8963b5f719819e4b",
            }
            logger.info("Using built-in Pyth symbol map")
        self._cache: dict[str, Price] = {}
        self._cache_ttl = 5  # seconds
        self._session: Optional[aiohttp.ClientSession] = None
        self._closed = False

    async def get_price(
        self, symbol: str, max_age_s: int = 5, max_dev_bps: int = 50
    ) -> Price:
        """Get price from Pyth Network with validation."""
        try:
            symbol = to_canonical(symbol)
            # Check cache first
            if symbol in self._cache:
                cached = self._cache[symbol]
                # Fix: Use unix timestamp comparison, not monotonic time
                import time

                current_unix = int(time.time())
                if cached.ts > (current_unix - self._cache_ttl):
                    return cached

            # Fetch from Pyth API
            price_id = self.symbol_map.get(symbol.upper())
            if not price_id:
                raise ValueError(f"Unsupported symbol: {symbol}")

            # Fix: Use persistent session to avoid connection flooding with request timeouts
            if self._session is None or self._session.closed:
                timeout = aiohttp.ClientTimeout(total=10, connect=5)
                self._session = aiohttp.ClientSession(timeout=timeout)

            params = {"ids[]": price_id}
            async with self._session.get(self.api_url, params=params) as response:
                if response.status != 200:
                    raise RuntimeError(f"Pyth API error: {response.status}")

                data = await response.json()
                price_data = data.get("parsed", [])

                if not price_data:
                    raise ValueError(f"No price data for {symbol}")

                # Extract price and confidence
                price_info = price_data[0]
                price_raw = int(price_info.get("price", 0))
                conf_raw = int(price_info.get("conf", 0))
                timestamp = int(price_info.get("publish_time", 0))
                expo = int(price_info.get("expo", 0))  # Fix: Include expo field

                # Fix: Apply expo scaling to produce 1e8 fixed-point integers
                # actual_price = price_raw * 10**expo (expo may be negative)
                # desired scale is 1e8 => price_1e8 = price_raw * 10**(expo + 8)
                from decimal import Decimal as _D

                price_1e8 = int(_D(price_raw) * (_D(10) ** (expo + 8)))
                conf_1e8 = int(_D(conf_raw) * (_D(10) ** (expo + 8)))

                # Validate confidence
                if conf_1e8 > price_1e8 * max_dev_bps // 10000:
                    raise ValueError(
                        f"Price confidence too high: {conf_1e8} > {price_1e8 * max_dev_bps // 10000}"
                    )

                # Check age - use unix timestamp
                import time

                current_time = int(time.time())
                age = current_time - timestamp
                if age > max_age_s:
                    raise ValueError(f"Price too stale: {age}s > {max_age_s}s")

                price = Price(
                    symbol=symbol,
                    price=price_1e8,
                    conf=conf_1e8,
                    ts=timestamp,
                    source="pyth",
                )

                # Cache the result
                self._cache[symbol] = price
                return price

        except Exception as e:
            logger.error(f"Pyth oracle error for {symbol}: {e}")
            raise ValueError(f"Failed to get price from Pyth: {e}")

    async def close(self):
        """Close the HTTP session to prevent resource leaks."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._closed = True
            logger.debug("Closed Pyth oracle HTTP session")

    def __del__(self):
        """Cleanup on deletion - fallback for unclosed sessions."""
        if hasattr(self, "_session") and self._session and not self._session.closed:
            logger.warning(
                "PythOracle session not properly closed - potential resource leak"
            )
            # Note: We can't await in __del__, so this is just a warning
