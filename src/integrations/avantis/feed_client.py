"""
Avantis Feed Client for Real-time Price Updates

This module provides real-time price feed integration using the Avantis FeedClient.
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any, Callable, Optional

from avantis_trader_sdk import FeedClient

logger = logging.getLogger(__name__)


@dataclass
class PriceUpdate:
    """Price update data structure"""

    pair: str
    price: float
    timestamp: int
    source: str = "pyth"


class AvantisFeedClient:
    """
    Real-time price feed client using Avantis FeedClient

    Handles WebSocket connections, reconnection logic, and price update callbacks.
    """

    def __init__(self, ws_url: Optional[str] = None):
        """
        Initialize the feed client

        Args:
            ws_url: WebSocket URL for price feeds (defaults to PYTH_WS_URL from env)
        """
        self.ws_url = ws_url or os.getenv("PYTH_WS_URL")
        self._client: Optional[FeedClient] = None
        self._callbacks: dict[str, Callable[[PriceUpdate], None]] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Reconnection settings
        self._reconnect_delay = 5
        self._max_reconnect_delay = 60

    def is_configured(self) -> bool:
        """
        Check if the feed client is properly configured

        Returns:
            bool: True if WebSocket URL is configured
        """
        return bool(self.ws_url)

    async def start(self, pair_callbacks: dict[str, Callable[[PriceUpdate], None]]):
        """
        Start the feed client with price update callbacks

        Args:
            pair_callbacks: Dictionary mapping pair names to callback functions
                e.g., {"ETH/USD": callback_function}
        """
        if not self.is_configured():
            logger.warning(
                "⚠️ Feed client not configured - skipping price feed startup"
            )
            return

        if self._running:
            logger.warning("⚠️ Feed client already running")
            return

        try:
            # Store callbacks
            self._callbacks = pair_callbacks.copy()

            # Create FeedClient
            self._client = FeedClient(
                ws_url=self.ws_url, on_error=self._on_error, on_close=self._on_close
            )

            logger.info(f"✅ FeedClient initialized with WebSocket: {self.ws_url}")

            # Register price feed callbacks
            for pair, callback in pair_callbacks.items():
                self._client.register_price_feed_callback(
                    pair, self._create_price_callback(pair, callback)
                )
                logger.info(f"✅ Registered price feed callback for {pair}")

            # Start listening for price updates
            self._running = True
            self._task = asyncio.create_task(self._listen_for_updates())

            logger.info("✅ FeedClient started successfully")

        except Exception as e:
            logger.error(f"❌ Failed to start FeedClient: {e}")
            self._running = False

    async def stop(self):
        """Stop the feed client"""
        if not self._running:
            return

        logger.info("🛑 Stopping FeedClient...")

        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        if self._client:
            try:
                await self._client.close()
            except Exception as e:
                logger.warning(f"⚠️ Error closing FeedClient: {e}")

        logger.info("✅ FeedClient stopped")

    async def _listen_for_updates(self):
        """Listen for price updates in background task"""
        while self._running:
            try:
                if self._client:
                    await self._client.listen_for_price_updates()
                else:
                    logger.error("❌ FeedClient not initialized")
                    break

            except Exception as e:
                logger.error(f"❌ Error in price update loop: {e}")

                if self._running:
                    logger.info(f"🔄 Reconnecting in {self._reconnect_delay} seconds...")
                    await asyncio.sleep(self._reconnect_delay)

                    # Exponential backoff for reconnection
                    self._reconnect_delay = min(
                        self._reconnect_delay * 2, self._max_reconnect_delay
                    )

                    try:
                        # Attempt to reconnect
                        if self._client:
                            await self._client.close()

                        # Recreate client
                        self._client = FeedClient(
                            ws_url=self.ws_url,
                            on_error=self._on_error,
                            on_close=self._on_close,
                        )

                        # Re-register callbacks
                        for pair, callback in self._callbacks.items():
                            self._client.register_price_feed_callback(
                                pair, self._create_price_callback(pair, callback)
                            )

                        logger.info("✅ FeedClient reconnected")

                    except Exception as reconnect_error:
                        logger.error(
                            f"❌ Failed to reconnect FeedClient: {reconnect_error}"
                        )
                else:
                    break

    def _create_price_callback(
        self, pair: str, callback: Callable[[PriceUpdate], None]
    ) -> Callable:
        """
        Create a price callback that wraps the user callback with error handling

        Args:
            pair: Trading pair (e.g., "ETH/USD")
            callback: User callback function

        Returns:
            Callable: Wrapped callback function
        """

        async def price_callback(price_data: Any):
            try:
                # Extract price data (structure depends on feed provider)
                price = float(price_data.get("price", 0))
                timestamp = int(price_data.get("timestamp", 0))

                price_update = PriceUpdate(
                    pair=pair, price=price, timestamp=timestamp, source="pyth"
                )

                # Call user callback
                if asyncio.iscoroutinefunction(callback):
                    await callback(price_update)
                else:
                    callback(price_update)

            except Exception as e:
                logger.error(f"❌ Error in price callback for {pair}: {e}")

        return price_callback

    def _on_error(self, error: Exception):
        """Handle WebSocket errors"""
        logger.error(f"❌ FeedClient WebSocket error: {error}")

    def _on_close(self, code: int, reason: str):
        """Handle WebSocket close events"""
        logger.warning(f"⚠️ FeedClient WebSocket closed: {code} - {reason}")

    def add_pair_callback(self, pair: str, callback: Callable[[PriceUpdate], None]):
        """
        Add a new price callback for a trading pair

        Args:
            pair: Trading pair (e.g., "ETH/USD")
            callback: Callback function for price updates
        """
        self._callbacks[pair] = callback

        if self._client and self._running:
            try:
                self._client.register_price_feed_callback(
                    pair, self._create_price_callback(pair, callback)
                )
                logger.info(f"✅ Added price callback for {pair}")
            except Exception as e:
                logger.error(f"❌ Failed to add price callback for {pair}: {e}")

    def remove_pair_callback(self, pair: str):
        """
        Remove a price callback for a trading pair

        Args:
            pair: Trading pair to remove
        """
        if pair in self._callbacks:
            del self._callbacks[pair]
            logger.info(f"✅ Removed price callback for {pair}")


# Global feed client instance
_feed_client: Optional[AvantisFeedClient] = None


def get_feed_client() -> AvantisFeedClient:
    """
    Get the global feed client instance

    Returns:
        AvantisFeedClient: Global feed client
    """
    global _feed_client

    if _feed_client is None:
        _feed_client = AvantisFeedClient()

    return _feed_client


def initialize_feed_client(ws_url: Optional[str] = None) -> AvantisFeedClient:
    """
    Initialize the global feed client

    Args:
        ws_url: WebSocket URL for price feeds (optional)

    Returns:
        AvantisFeedClient: Initialized feed client
    """
    global _feed_client

    _feed_client = AvantisFeedClient(ws_url)
    return _feed_client
