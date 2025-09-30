"""Gas policy for EIP-1559 transactions with caps and surge controls."""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class GasPolicy:
    """Gas policy for EIP-1559 transactions."""

    max_fee_cap_gwei: int = 150  # Maximum base fee in Gwei
    max_priority_gwei: int = 2  # Maximum priority fee in Gwei
    surge_multiplier: float = 1.2  # Multiplier for high network activity
    min_priority_gwei: int = 1  # Minimum priority fee in Gwei

    def quote(self, web3_client) -> tuple[int, int]:
        """Get gas price quote for EIP-1559 transaction.

        Args:
            web3_client: Web3 client instance

        Returns:
            Tuple of (max_fee_per_gas, max_priority_fee_per_gas) in wei
        """
        try:
            # Get current base fee
            base_fee = web3_client.eth.gas_price

            # Apply surge multiplier if network is busy
            max_fee = int(
                min(
                    base_fee * self.surge_multiplier,
                    self.max_fee_cap_gwei * 1e9,  # Convert Gwei to wei
                )
            )

            # Set priority fee (tip to miner)
            max_priority = int(self.max_priority_gwei * 1e9)

            # Ensure minimum priority fee
            min_priority = int(self.min_priority_gwei * 1e9)
            max_priority = max(max_priority, min_priority)

            logger.debug(f"Gas quote: max_fee={max_fee}, priority={max_priority}")
            return max_fee, max_priority

        except Exception as e:
            logger.error(f"Failed to get gas quote: {e}")
            # Fallback to conservative values
            fallback_max_fee = int(self.max_fee_cap_gwei * 1e9)
            fallback_priority = int(self.max_priority_gwei * 1e9)
            logger.warning(
                f"Using fallback gas values: {fallback_max_fee}, {fallback_priority}"
            )
            return fallback_max_fee, fallback_priority

    def bump_fee(self, current_max_fee: int, bump_percent: float = 0.15) -> int:
        """Bump the max fee for retry scenarios.

        Args:
            current_max_fee: Current max fee in wei
            bump_percent: Percentage to bump (default 15%)

        Returns:
            New max fee in wei
        """
        bumped = int(current_max_fee * (1 + bump_percent))
        capped = min(bumped, int(self.max_fee_cap_gwei * 1e9))

        logger.debug(f"Bumped fee from {current_max_fee} to {capped}")
        return capped
