"""
Pyth price feed adapter - handles Pyth Network price data.

This module provides clean interfaces for fetching and parsing
Pyth price updates via Hermes API and WebSocket.
"""

import asyncio
import logging
from decimal import Decimal
from typing import Any, Optional

import aiohttp

from ..core.models import PriceInfo

logger = logging.getLogger(__name__)


class PythFeedAdapter:
    """Adapter for Pyth Network price feeds."""

    def __init__(self, hermes_endpoint: str, ws_url: Optional[str] = None):
        """
        Initialize Pyth feed adapter.

        Args:
            hermes_endpoint: Pyth Hermes HTTP endpoint
            ws_url: Optional WebSocket URL for real-time updates
        """
        self.hermes_endpoint = hermes_endpoint
        self.ws_url = ws_url
        self.session: Optional[aiohttp.ClientSession] = None

        logger.info("Pyth Feed Adapter initialized")
        logger.info(f"  Hermes Endpoint: {hermes_endpoint}")
        if ws_url:
            logger.info(f"  WebSocket URL: {ws_url}")

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def get_latest_prices(self, pair_ids: list[str]) -> dict[str, PriceInfo]:
        """
        Get latest prices for specified pairs.

        Args:
            pair_ids: List of Pyth pair identifiers

        Returns:
            Dictionary mapping pair_id to PriceInfo
        """
        if not self.session:
            raise RuntimeError("Adapter not initialized - use async context manager")

        try:
            # Fetch latest price updates
            url = f"{self.hermes_endpoint}?ids[]={'&ids[]='.join(pair_ids)}"

            async with self.session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}: {await response.text()}")

                data = await response.json()

                # Parse price updates
                prices = {}
                for update in data.get("parsed", []):
                    pair_id = update.get("id")
                    if pair_id in pair_ids:
                        price_info = self._parse_price_update(update)
                        if price_info:
                            prices[pair_id] = price_info

                logger.info(f"Fetched {len(prices)} price updates from Pyth")
                return prices

        except Exception as e:
            logger.error(f"Failed to fetch Pyth prices: {e}")
            raise

    def _parse_price_update(self, update: dict[str, Any]) -> Optional[PriceInfo]:
        """
        Parse a single price update from Pyth.

        Args:
            update: Raw price update data

        Returns:
            Parsed PriceInfo or None if invalid
        """
        try:
            # Extract price information
            price_data = update.get("price", {})
            price = Decimal(str(price_data.get("price", 0)))

            # Extract metadata
            pair_id = update.get("id", "")
            timestamp = update.get("publish_time", 0)

            # Map pair ID to pair index (this would need to be configured)
            pair_index = self._map_pair_id_to_index(pair_id)

            return PriceInfo(
                pair_index=pair_index, price=price, timestamp=timestamp, source="pyth"
            )

        except Exception as e:
            logger.warning(f"Failed to parse price update: {e}")
            return None

    def _map_pair_id_to_index(self, pair_id: str) -> int:
        """
        Map Pyth pair ID to internal pair index.

        Args:
            pair_id: Pyth pair identifier

        Returns:
            Internal pair index
        """
        # This mapping would need to be configured based on your trading pairs
        pair_mapping = {
            "crypto.BTC/USD": 0,
            "crypto.ETH/USD": 1,
            "crypto.SOL/USD": 2,
            # Add more mappings as needed
        }

        return pair_mapping.get(pair_id, 0)  # Default to pair 0

    async def stream_price_updates(
        self, pair_ids: list[str], callback: callable, interval: float = 5.0
    ) -> None:
        """
        Stream price updates for specified pairs.

        Args:
            pair_ids: List of Pyth pair identifiers
            callback: Callback function to handle price updates
            interval: Update interval in seconds
        """
        logger.info(f"Starting price stream for {len(pair_ids)} pairs")

        while True:
            try:
                prices = await self.get_latest_prices(pair_ids)

                for pair_id, price_info in prices.items():
                    await callback(pair_id, price_info)

                await asyncio.sleep(interval)

            except Exception as e:
                logger.error(f"Error in price stream: {e}")
                await asyncio.sleep(interval)  # Continue despite errors

    async def get_btc_price(self) -> Optional[PriceInfo]:
        """Get current BTC price from Pyth."""
        prices = await self.get_latest_prices(["crypto.BTC/USD"])
        return prices.get("crypto.BTC/USD")

    async def get_eth_price(self) -> Optional[PriceInfo]:
        """Get current ETH price from Pyth."""
        prices = await self.get_latest_prices(["crypto.ETH/USD"])
        return prices.get("crypto.ETH/USD")

    async def get_sol_price(self) -> Optional[PriceInfo]:
        """Get current SOL price from Pyth."""
        prices = await self.get_latest_prices(["crypto.SOL/USD"])
        return prices.get("crypto.SOL/USD")


class ChainlinkFeedAdapter:
    """Adapter for Chainlink price feeds."""

    def __init__(self, rpc_url: str, feed_addresses: dict[str, str]):
        """
        Initialize Chainlink feed adapter.

        Args:
            rpc_url: RPC endpoint for blockchain calls
            feed_addresses: Dictionary mapping pair names to feed addresses
        """
        self.rpc_url = rpc_url
        self.feed_addresses = feed_addresses

        logger.info("Chainlink Feed Adapter initialized")
        logger.info(f"  RPC URL: {rpc_url}")
        logger.info(f"  Feed addresses: {len(feed_addresses)} feeds")

    async def get_latest_price(self, pair_name: str) -> Optional[PriceInfo]:
        """
        Get latest price for a specific pair.

        Args:
            pair_name: Name of the trading pair

        Returns:
            PriceInfo with current price or None if unavailable
        """
        feed_address = self.feed_addresses.get(pair_name)
        if not feed_address:
            logger.warning(f"No Chainlink feed address for pair: {pair_name}")
            return None

        try:
            # This would need Web3 integration for actual Chainlink calls
            # For now, return a placeholder
            logger.info(
                f"Would fetch Chainlink price for {pair_name} at {feed_address}"
            )

            return PriceInfo(
                pair_index=0,  # Would need proper mapping
                price=Decimal("50000"),  # Placeholder price
                timestamp=0,  # Would get from contract
                source="chainlink",
            )

        except Exception as e:
            logger.error(f"Failed to get Chainlink price for {pair_name}: {e}")
            return None
