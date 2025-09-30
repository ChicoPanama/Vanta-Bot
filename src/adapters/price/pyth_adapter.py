"""Pyth price adapter with HTTP API integration."""

import logging
from typing import Optional

import requests

from .base import PriceFeed, PriceQuote

logger = logging.getLogger(__name__)


class PythAdapter(PriceFeed):
    """Pyth Network price feed adapter."""

    def __init__(self, endpoint: str, price_ids: Optional[dict[str, str]] = None):
        """Initialize Pyth adapter.

        Args:
            endpoint: Pyth Hermes endpoint URL
            price_ids: Map of symbol to Pyth price ID
                e.g., {"BTC-USD": "0xe62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43"}
        """
        self.endpoint = endpoint
        self.price_ids = price_ids or {}

    def get_price(self, symbol: str) -> Optional[PriceQuote]:
        """Get price from Pyth Network.

        Args:
            symbol: Market symbol (e.g., "BTC-USD")

        Returns:
            PriceQuote or None if not available
        """
        price_id = self.price_ids.get(symbol)
        if not price_id:
            logger.debug(f"No Pyth price ID configured for {symbol}")
            return None

        try:
            # Call Pyth Hermes HTTP API
            url = f"{self.endpoint}?ids[]={price_id}"
            response = requests.get(url, timeout=5)
            response.raise_for_status()

            data = response.json()

            # Parse response: data['parsed'][0] contains price feed
            if not data.get("parsed") or len(data["parsed"]) == 0:
                logger.warning(f"No price data returned from Pyth for {symbol}")
                return None

            feed = data["parsed"][0]
            price_data = feed["price"]

            # Pyth returns price as int with exponent
            # e.g., price=6345123, expo=-8 means 63451.23
            price = int(price_data["price"])
            expo = int(price_data["expo"])
            conf = int(price_data["conf"])  # confidence interval

            # Convert to normalized form (price * 10^-expo)
            # We'll return the price in the original form and decimals as -expo
            # so the caller can do: actual_price = price / (10 ** decimals)
            decimals = -expo

            logger.debug(f"Pyth price for {symbol}: {price} (expo={expo}, conf={conf})")

            return PriceQuote(
                symbol=symbol,
                price=price,
                decimals=decimals,
                timestamp=feed.get("publish_time", 0),
                source="pyth",
            )

        except requests.RequestException as e:
            logger.error(f"Failed to fetch Pyth price for {symbol}: {e}")
            return None
        except (KeyError, ValueError, IndexError) as e:
            logger.error(f"Failed to parse Pyth response for {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting Pyth price for {symbol}: {e}")
            return None
