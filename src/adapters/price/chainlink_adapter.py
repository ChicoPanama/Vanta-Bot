"""Chainlink price adapter (Phase 3)."""

import logging
import time
from typing import Optional

from web3 import Web3

from .base import PriceFeed, PriceQuote

logger = logging.getLogger(__name__)

# Minimal Chainlink Aggregator ABI
CHAINLINK_AGG_ABI = [
    {
        "inputs": [],
        "name": "latestRoundData",
        "outputs": [
            {"internalType": "uint80", "name": "roundId", "type": "uint80"},
            {"internalType": "int256", "name": "answer", "type": "int256"},
            {"internalType": "uint256", "name": "startedAt", "type": "uint256"},
            {"internalType": "uint256", "name": "updatedAt", "type": "uint256"},
            {"internalType": "uint80", "name": "answeredInRound", "type": "uint80"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function",
    },
]


class ChainlinkAdapter(PriceFeed):
    """Chainlink price feed adapter."""

    def __init__(self, w3: Web3, symbol_to_feed: dict[str, str]):
        """Initialize Chainlink adapter.

        Args:
            w3: Web3 instance
            symbol_to_feed: Map of symbol to Chainlink feed address
                e.g., {"BTC-USD": "0x64c911996D3c6aC71f9b455B1E8E7266BcbD848F"}
        """
        self.w3 = w3
        self.feeds = {k: Web3.to_checksum_address(v) for k, v in symbol_to_feed.items()}

    def get_price(self, symbol: str) -> Optional[PriceQuote]:
        """Get price from Chainlink feed.

        Args:
            symbol: Market symbol (e.g., "BTC-USD")

        Returns:
            PriceQuote or None if not available
        """
        feed_address = self.feeds.get(symbol)
        if not feed_address:
            logger.debug(f"No Chainlink feed configured for {symbol}")
            return None

        try:
            contract = self.w3.eth.contract(address=feed_address, abi=CHAINLINK_AGG_ABI)

            # Get decimals
            decimals = contract.functions.decimals().call()

            # Get latest price
            round_data = contract.functions.latestRoundData().call()
            round_id, answer, started_at, updated_at, answered_in_round = round_data

            # Validate price
            if int(answer) <= 0:
                logger.warning(f"Invalid Chainlink price for {symbol}: {answer}")
                return None

            logger.debug(
                f"Chainlink {symbol}: price={answer}, decimals={decimals}, updated={updated_at}"
            )

            return PriceQuote(
                symbol=symbol,
                price=int(answer),
                decimals=int(decimals),
                source="chainlink",
                timestamp=int(updated_at),
            )

        except Exception as e:
            logger.error(f"Failed to get Chainlink price for {symbol}: {e}")
            return None
