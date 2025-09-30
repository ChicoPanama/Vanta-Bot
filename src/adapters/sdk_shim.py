"""
Optional SDK shim - minimal wrapper around Avantis SDK if needed.

This module provides a controlled interface to the Avantis SDK,
enforcing human-in, SDK-scales-once behavior to prevent double-scaling.
"""

import logging
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)


class SDKShim:
    """
    Controlled wrapper around Avantis SDK to prevent double-scaling.

    This shim enforces the rule: human values in, SDK handles scaling.
    It should only be used if the SDK is absolutely necessary and
    has been verified to not double-scale.
    """

    def __init__(self, use_sdk: bool = False):
        """
        Initialize SDK shim.

        Args:
            use_sdk: Whether to actually use the SDK (disabled by default)
        """
        self.use_sdk = use_sdk
        self.sdk_instance = None

        if use_sdk:
            try:
                # Import SDK only if explicitly enabled
                from avantis_sdk import AvantisTrader  # type: ignore

                self.sdk_instance = AvantisTrader()
                logger.info("SDK shim initialized with Avantis SDK")
            except ImportError:
                logger.error(
                    "Avantis SDK not available - falling back to direct contract calls"
                )
                self.use_sdk = False

        if not use_sdk:
            logger.info("SDK shim initialized in bypass mode (direct contract calls)")

    def open_trade(
        self,
        collateral_usdc: Decimal,
        leverage_x: Decimal,
        slippage_pct: Decimal,
        pair_index: int,
        is_long: bool,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Open a trade using controlled SDK interface.

        This method enforces human-in, SDK-scales-once behavior:
        - Inputs are in human-readable units
        - SDK handles all scaling internally
        - No pre-scaling allowed

        Args:
            collateral_usdc: Collateral in USDC (e.g., 100.0 for $100)
            leverage_x: Leverage multiplier (e.g., 5.0 for 5x)
            slippage_pct: Slippage percentage (e.g., 1.0 for 1%)
            pair_index: Trading pair index
            is_long: True for long, False for short
            **kwargs: Additional parameters

        Returns:
            Dictionary with trade result

        Raises:
            ValueError: If SDK is not available or parameters are invalid
        """
        if not self.use_sdk or not self.sdk_instance:
            raise ValueError("SDK not available - use direct contract calls instead")

        # Validate that inputs are in human units (not pre-scaled)
        self._validate_human_units(collateral_usdc, leverage_x, slippage_pct)

        try:
            # Pass human units directly to SDK - let it handle scaling
            result = self.sdk_instance.open_trade(
                collateral=collateral_usdc,
                leverage=leverage_x,
                slippage=slippage_pct,
                pair_index=pair_index,
                is_long=is_long,
                **kwargs,
            )

            logger.info("Trade executed via SDK shim")
            return result

        except Exception as e:
            logger.error(f"SDK trade failed: {e}")
            raise

    def _validate_human_units(
        self, collateral_usdc: Decimal, leverage_x: Decimal, slippage_pct: Decimal
    ) -> None:
        """
        Validate that inputs are in human-readable units, not pre-scaled.

        Args:
            collateral_usdc: Collateral amount
            leverage_x: Leverage multiplier
            slippage_pct: Slippage percentage

        Raises:
            ValueError: If inputs appear to be pre-scaled
        """
        # Check for obvious pre-scaling indicators

        # Collateral should be reasonable (not in wei-like units)
        if collateral_usdc > 1000000:  # $1M seems like a reasonable max
            raise ValueError(
                f"Collateral {collateral_usdc} appears pre-scaled (too large)"
            )

        # Leverage should be reasonable (not in 1e10 scale)
        if leverage_x > 1000:  # 1000x leverage is way too high
            raise ValueError(f"Leverage {leverage_x} appears pre-scaled (too large)")

        # Slippage should be reasonable (not in 1e10 scale)
        if slippage_pct > 100:  # 100% slippage is way too high
            raise ValueError(f"Slippage {slippage_pct} appears pre-scaled (too large)")

        logger.debug("Human unit validation passed")

    def is_available(self) -> bool:
        """
        Check if SDK is available and usable.

        Returns:
            True if SDK is available, False otherwise
        """
        return self.use_sdk and self.sdk_instance is not None

    def get_sdk_info(self) -> dict[str, Any]:
        """
        Get information about the SDK instance.

        Returns:
            Dictionary with SDK information
        """
        if not self.is_available():
            return {"available": False, "reason": "SDK not initialized"}

        return {
            "available": True,
            "type": "Avantis SDK",
            "version": getattr(self.sdk_instance, "__version__", "unknown"),
        }


def create_sdk_shim(use_sdk: bool = False) -> SDKShim:
    """
    Factory function to create SDK shim with proper configuration.

    Args:
        use_sdk: Whether to enable SDK usage

    Returns:
        Configured SDK shim instance
    """
    return SDKShim(use_sdk=use_sdk)
