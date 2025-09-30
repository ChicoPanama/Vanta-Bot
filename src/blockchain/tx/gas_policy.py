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
            # Get latest block to read baseFeePerGas
            latest_block = web3_client.eth.get_block("latest")
            base_fee = latest_block.get("baseFeePerGas")

            if base_fee is None:
                # Fallback for non-EIP-1559 chains (shouldn't happen on Base)
                gas_price = int(web3_client.eth.gas_price * 1.2)
                priority = int(gas_price * 0.1)
                logger.warning(
                    "No baseFeePerGas found; using legacy gas_price fallback"
                )
                return gas_price, priority

            # Set priority fee (tip to miner)
            priority_wei = int(self.max_priority_gwei * 1e9)

            # Calculate max fee: base + priority, with safety multiplier
            max_fee = int((base_fee + priority_wei) * self.surge_multiplier)

            # Cap to prevent excessive fees
            max_fee_cap_wei = int(self.max_fee_cap_gwei * 1e9)
            max_fee = min(max_fee, max_fee_cap_wei)

            # Ensure minimum priority fee
            min_priority_wei = int(self.min_priority_gwei * 1e9)
            priority_wei = max(priority_wei, min_priority_wei)

            logger.debug(
                f"EIP-1559 gas quote: base={base_fee}, max_fee={max_fee}, priority={priority_wei}"
            )
            return max_fee, priority_wei

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
