"""Nonce management with Redis locks to prevent collisions."""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from redis import Redis

from .nonce_store import HybridNonceStore

logger = logging.getLogger(__name__)


class NonceManager:
    """Manages nonce reservation per address to prevent transaction collisions."""

    def __init__(self, redis_client: Optional[Redis], web3_client):
        """Initialize with Redis client and Web3 client.

        Args:
            redis_client: Redis client (can be None for fallback-only mode)
            web3_client: Web3 client for on-chain nonce queries
        """
        self.web3 = web3_client
        self.store = HybridNonceStore(redis_client, web3_client)

    @asynccontextmanager
    async def reserve(self, address: str):
        """Reserve a nonce for the given address.

        Args:
            address: Ethereum address to reserve nonce for

        Yields:
            int: The reserved nonce

        Raises:
            RuntimeError: If all nonce stores fail
        """
        try:
            async with self.store.reserve(address) as nonce:
                logger.debug(f"Reserved nonce {nonce} for {address}")
                yield nonce
        except Exception as e:
            logger.error(f"Failed to reserve nonce for {address}: {e}")
            raise RuntimeError(f"Nonce reservation failed for {address}: {e}")

    def release_nonce(self, address: str, nonce: int):
        """Release a nonce back to the pool (for failed transactions).

        Note: This is a simplified implementation. In production, you'd want
        to implement proper nonce release logic in the store.
        """
        try:
            logger.debug(f"Released nonce {nonce} for {address}")
            # In a full implementation, you'd update the store here
        except Exception as e:
            logger.error(f"Failed to release nonce {nonce} for {address}: {e}")

    def get_current_nonce(self, address: str) -> int:
        """Get current nonce for address without reserving."""
        try:
            return self.web3.eth.get_transaction_count(address, "pending")
        except Exception as e:
            logger.error(f"Failed to get current nonce for {address}: {e}")
            raise
