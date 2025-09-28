"""Nonce management with Redis locks to prevent collisions."""

import time
import logging
from contextlib import contextmanager
from typing import Optional
from redis import Redis

logger = logging.getLogger(__name__)


class NonceManager:
    """Manages nonce reservation per address to prevent transaction collisions."""
    
    def __init__(self, redis_client: Redis, web3_client):
        self.redis = redis_client
        self.web3 = web3_client
        self.lock_timeout = 5  # seconds
        self.blocking_timeout = 5  # seconds
        self.nonce_cache_ttl = 300  # 5 minutes

    @contextmanager
    def reserve(self, address: str):
        """Reserve a nonce for the given address.
        
        Args:
            address: Ethereum address to reserve nonce for
            
        Yields:
            int: The reserved nonce
            
        Raises:
            RuntimeError: If lock acquisition fails
        """
        key = f"nonce:{address.lower()}"
        lock_key = f"{key}:lock"
        
        try:
            # Acquire distributed lock
            with self.redis.lock(
                lock_key, 
                timeout=self.lock_timeout, 
                blocking_timeout=self.blocking_timeout
            ):
                # Get current on-chain nonce
                onchain_nonce = self.web3.eth.get_transaction_count(address, "pending")
                
                # Get cached nonce from Redis
                cached_nonce = self.redis.get(key)
                if cached_nonce is not None:
                    cached_nonce = int(cached_nonce)
                else:
                    cached_nonce = onchain_nonce
                
                # Use the higher of on-chain or cached nonce
                next_nonce = max(onchain_nonce, cached_nonce)
                
                # Update cache with next nonce
                self.redis.set(key, next_nonce + 1, ex=self.nonce_cache_ttl)
                
                logger.debug(f"Reserved nonce {next_nonce} for {address}")
                yield next_nonce
                
        except Exception as e:
            logger.error(f"Failed to reserve nonce for {address}: {e}")
            raise RuntimeError(f"Nonce reservation failed for {address}: {e}")

    def release_nonce(self, address: str, nonce: int):
        """Release a nonce back to the pool (for failed transactions)."""
        key = f"nonce:{address.lower()}"
        try:
            # Only release if it's the next expected nonce
            current = self.redis.get(key)
            if current and int(current) == nonce + 1:
                self.redis.set(key, nonce, ex=self.nonce_cache_ttl)
                logger.debug(f"Released nonce {nonce} for {address}")
        except Exception as e:
            logger.error(f"Failed to release nonce {nonce} for {address}: {e}")

    def get_current_nonce(self, address: str) -> int:
        """Get current nonce for address without reserving."""
        try:
            onchain_nonce = self.web3.eth.get_transaction_count(address, "pending")
            cached_nonce = self.redis.get(f"nonce:{address.lower()}")
            
            if cached_nonce is not None:
                return max(onchain_nonce, int(cached_nonce))
            return onchain_nonce
        except Exception as e:
            logger.error(f"Failed to get current nonce for {address}: {e}")
            raise
