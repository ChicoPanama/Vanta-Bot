"""Market and feed validators (Phase 3)."""

import logging

from web3 import Web3

from src.services.markets.market_catalog import default_market_catalog

logger = logging.getLogger(__name__)


def validate_markets_and_feeds(w3: Web3) -> None:
    """Validate market configuration.

    Args:
        w3: Web3 instance

    Raises:
        AssertionError: If market config is invalid
    """
    markets = default_market_catalog()

    logger.info(f"Validating {len(markets)} markets...")

    for sym, market in markets.items():
        # Validate perpetual address
        assert w3.is_address(market.perpetual), (
            f"Invalid perp address for {sym}: {market.perpetual}"
        )

        # Validate min position size is set
        assert market.min_position_usd > 0, f"min_position_usd not set for {sym}"

        # Validate market ID
        assert market.market_id >= 0, f"Invalid market_id for {sym}"

        logger.debug(
            f"✅ Market {sym} validated: id={market.market_id}, min=${market.min_position_usd / 1e6}"
        )

    logger.info(f"✅ All {len(markets)} markets validated")
