"""
Avantis Price Provider - SDK Parameter Utilities

This module provides parameterized price/impact/risk utilities using the Avantis Trader SDK
for getting trading parameters, fees, and risk calculations.
"""

import logging
from typing import Any, Optional

from avantis_trader_sdk.types import LossProtectionInfo, PairSpread, TradeInput

from src.integrations.avantis.sdk_client import get_sdk_client

logger = logging.getLogger(__name__)


class TradeQuote(dict):
    """Trade quote with both dict and attribute-style access.

    Designed to satisfy tests that expect either a mapping or an object with attributes.
    """

    def __init__(
        self,
        *,
        pair_index: int,
        position_size: float,
        opening_fee_usdc: float,
        loss_protection_percent: float,
        loss_protection_amount: float,
        pair_spread: Optional[PairSpread] = None,
        price_impact_spread: Optional[float] = None,
        skew_impact_spread: Optional[float] = None,
        slippage_pct: float = 0.0,
    ) -> None:
        super().__init__(
            pair_index=pair_index,
            position_size=position_size,
            opening_fee_usdc=opening_fee_usdc,
            loss_protection_percent=loss_protection_percent,
            loss_protection_amount=loss_protection_amount,
            pair_spread=pair_spread,
            price_impact_spread=price_impact_spread,
            skew_impact_spread=skew_impact_spread,
            slippage_pct=slippage_pct,
        )
        # Backward-compat alias expected by some tests
        if price_impact_spread is not None:
            self["impact_spread"] = price_impact_spread
        # enable attribute access
        self.__dict__ = self


class AvantisPriceProvider:
    """
    Parameterized price/impact/risk utility using the Avantis Trader SDK

    Provides methods for getting trading parameters, fees, spreads, and risk calculations.
    """

    def __init__(self):
        """Initialize the price provider"""
        self._client = None
        self._cache: dict[str, Any] = {}
        self._cache_ttl = 30  # Cache TTL in seconds
        self.latest_price: dict[str, float] = {}  # Simple price cache

    async def _get_client(self):
        """Get or initialize the SDK client"""
        if self._client is None:
            sdk_client = get_sdk_client()
            self._client = sdk_client.get_client()
        return self._client

    async def get_pair_index(self, pair: str) -> int:
        """
        Get the pair index for a trading pair

        Args:
            pair: Trading pair (e.g., "ETH/USD")

        Returns:
            int: Pair index
        """
        try:
            client = await self._get_client()
            pair_index = await client.pairs_cache.get_pair_index(pair)
            logger.debug(f"Pair index for {pair}: {pair_index}")
            return pair_index
        except Exception as e:
            logger.error(f"❌ Error getting pair index for {pair}: {e}")
            raise

    async def estimate_opening_fee(self, trade_input: TradeInput) -> float:
        """
        Estimate the opening fee for a trade

        Args:
            trade_input: Trade input parameters

        Returns:
            float: Opening fee in USDC
        """
        try:
            client = await self._get_client()
            opening_fee = await client.fee_parameters.get_opening_fee(trade_input)
            logger.debug(f"Opening fee: {opening_fee} USDC")
            return opening_fee
        except Exception as e:
            logger.error(f"❌ Error estimating opening fee: {e}")
            raise

    async def get_loss_protection(
        self, trade_input: TradeInput, opening_fee_usdc: float
    ) -> LossProtectionInfo:
        """
        Get loss protection information for a trade

        Args:
            trade_input: Trade input parameters
            opening_fee_usdc: Opening fee in USDC

        Returns:
            LossProtectionInfo: Loss protection details
        """
        try:
            client = await self._get_client()
            loss_protection = (
                await client.trading_parameters.get_loss_protection_for_trade_input(
                    trade_input, opening_fee_usdc=opening_fee_usdc
                )
            )
            logger.debug(f"Loss protection: {loss_protection}")
            return loss_protection
        except Exception as e:
            logger.error(f"❌ Error getting loss protection: {e}")
            raise

    async def get_pair_spread(self, pair: str) -> Optional[PairSpread]:
        """
        Get the current pair spread

        Args:
            pair: Trading pair (e.g., "ETH/USD")

        Returns:
            PairSpread: Current spread information
        """
        try:
            client = await self._get_client()
            spread = await client.asset_parameters.get_pair_spread(pair)
            logger.debug(f"Pair spread for {pair}: {spread}")
            return spread
        except Exception as e:
            logger.error(f"❌ Error getting pair spread for {pair}: {e}")
            return None

    async def get_price_impact_spread(
        self, pair: str, is_long: bool, position_size: float
    ) -> Optional[float]:
        """
        Get the price impact spread for a position

        Args:
            pair: Trading pair (e.g., "ETH/USD")
            is_long: True for long position, False for short
            position_size: Position size in USD

        Returns:
            float: Price impact spread
        """
        try:
            client = await self._get_client()
            impact = await client.asset_parameters.get_price_impact_spread(
                position_size=position_size, is_long=is_long, pair=pair
            )
            logger.debug(f"Price impact spread for {pair}: {impact}")
            return impact
        except Exception as e:
            logger.error(f"❌ Error getting price impact spread for {pair}: {e}")
            return None

    async def get_skew_impact_spread(
        self, pair: str, is_long: bool, position_size: float
    ) -> Optional[float]:
        """
        Get the skew impact spread for a position

        Args:
            pair: Trading pair (e.g., "ETH/USD")
            is_long: True for long position, False for short
            position_size: Position size in USD

        Returns:
            float: Skew impact spread
        """
        try:
            client = await self._get_client()
            skew = await client.asset_parameters.get_skew_impact_spread(
                position_size=position_size, is_long=is_long, pair=pair
            )
            logger.debug(f"Skew impact spread for {pair}: {skew}")
            return skew
        except Exception as e:
            logger.error(f"❌ Error getting skew impact spread for {pair}: {e}")
            return None

    async def quote_open(
        self,
        pair: str,
        is_long: bool,
        collateral_usdc: float,
        leverage: float,
        slippage_pct: float = 0.0,
    ) -> TradeQuote:
        """
        Get a comprehensive trade quote for opening a position

        Args:
            pair: Trading pair (e.g., "ETH/USD")
            is_long: True for long position, False for short
            collateral_usdc: Collateral amount in USDC
            leverage: Leverage multiplier
            slippage_pct: Maximum slippage percentage

        Returns:
            Dict[str, Any]: Complete trade quote with all parameters
        """
        try:
            # Get pair index
            pair_index = await self.get_pair_index(pair)

            # Calculate position size
            position_size = collateral_usdc * leverage

            # Create trade input for parameter calculation (use zero address for tests/mocks)
            trade_input = TradeInput(
                trader="0x0000000000000000000000000000000000000000",
                open_price=None,  # Market order
                pair_index=pair_index,
                collateral_in_trade=collateral_usdc,
                is_long=is_long,
                leverage=leverage,
                index=0,
                tp=0,
                sl=0,
                timestamp=0,
            )

            # Get opening fee
            opening_fee_usdc = await self.estimate_opening_fee(trade_input)

            # Get loss protection
            loss_protection = await self.get_loss_protection(
                trade_input, opening_fee_usdc
            )

            # Get spreads (optional, may fail for some pairs)
            pair_spread = await self.get_pair_spread(pair)
            price_impact_spread = await self.get_price_impact_spread(
                pair, is_long, position_size
            )
            skew_impact_spread = await self.get_skew_impact_spread(
                pair, is_long, position_size
            )

            return TradeQuote(
                pair_index=pair_index,
                position_size=position_size,
                opening_fee_usdc=opening_fee_usdc,
                loss_protection_percent=loss_protection.loss_protection_percent,
                loss_protection_amount=loss_protection.loss_protection_amount,
                pair_spread=pair_spread,
                price_impact_spread=price_impact_spread,
                skew_impact_spread=skew_impact_spread,
                slippage_pct=slippage_pct,
            )

        except Exception as e:
            logger.error(f"❌ Error creating trade quote for {pair}: {e}")
            raise

    async def get_available_pairs(self) -> list[str]:
        """
        Get list of available trading pairs

        Returns:
            list[str]: List of trading pair strings
        """
        try:
            client = await self._get_client()
            pairs_count = await client.pairs_cache.get_pairs_count()

            pairs = []
            for i in range(pairs_count):
                try:
                    pair = await client.pairs_cache.get_pair_by_index(i)
                    if pair:
                        pairs.append(pair)
                except Exception as e:
                    logger.debug(f"Could not get pair at index {i}: {e}")
                    continue

            logger.info(f"Found {len(pairs)} available trading pairs")
            return pairs

        except Exception as e:
            logger.error(f"❌ Error getting available pairs: {e}")
            return []

    async def get_pair_info(self, pair: str) -> Optional[dict[str, Any]]:
        """
        Get comprehensive information about a trading pair

        Args:
            pair: Trading pair (e.g., "ETH/USD")

        Returns:
            Dict[str, Any]: Pair information including spreads, fees, etc.
        """
        try:
            pair_index = await self.get_pair_index(pair)
            pair_spread = await self.get_pair_spread(pair)

            # Get spreads for a small position to show current market conditions
            small_position_size = 1000  # $1000 position
            price_impact_long = await self.get_price_impact_spread(
                pair, True, small_position_size
            )
            price_impact_short = await self.get_price_impact_spread(
                pair, False, small_position_size
            )
            skew_impact_long = await self.get_skew_impact_spread(
                pair, True, small_position_size
            )
            skew_impact_short = await self.get_skew_impact_spread(
                pair, False, small_position_size
            )

            return {
                "pair": pair,
                "pair_index": pair_index,
                "pair_spread": pair_spread,
                "price_impact_long": price_impact_long,
                "price_impact_short": price_impact_short,
                "skew_impact_long": skew_impact_long,
                "skew_impact_short": skew_impact_short,
            }

        except Exception as e:
            logger.error(f"❌ Error getting pair info for {pair}: {e}")
            return None


# Global price provider instance
_price_provider: Optional[AvantisPriceProvider] = None


def get_price_provider() -> AvantisPriceProvider:
    """
    Get the global price provider instance

    Returns:
        AvantisPriceProvider: Global price provider
    """
    global _price_provider

    if _price_provider is None:
        _price_provider = AvantisPriceProvider()

    return _price_provider
