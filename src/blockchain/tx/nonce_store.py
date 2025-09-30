"""Nonce store implementations with fallback strategies."""

import asyncio
import concurrent.futures
import logging
from contextlib import asynccontextmanager
from typing import Protocol

logger = logging.getLogger(__name__)


class NonceStore(Protocol):
    """Protocol for nonce storage."""

    @asynccontextmanager
    async def reserve(self, address: str):
        """Reserve a nonce for the given address."""
        ...


class InMemoryNonceStore:
    """In-memory nonce store with asyncio locks as fallback."""

    def __init__(self):
        self._nonces: dict[str, int] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

    @asynccontextmanager
    async def reserve(self, address: str):
        """Reserve a nonce using in-memory store."""
        # Get or create lock for this address
        if address not in self._locks:
            self._locks[address] = asyncio.Lock()

        lock = self._locks[address]

        try:
            # Acquire lock properly in async context
            await lock.acquire()

            # Get current nonce
            current_nonce = self._nonces.get(address, 0)
            next_nonce = current_nonce + 1

            # Update stored nonce
            self._nonces[address] = next_nonce

            logger.debug(f"Reserved in-memory nonce {next_nonce} for {address}")
            yield next_nonce

        finally:
            # Release lock
            lock.release()


class RedisNonceStore:
    """Redis-based nonce store with distributed locking."""

    def __init__(self, redis_client, web3_client):
        self.redis = redis_client
        self.web3 = web3_client
        self.lock_timeout = 5  # seconds
        self.blocking_timeout = 5  # seconds
        self.nonce_cache_ttl = 300  # 5 minutes
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

    @asynccontextmanager
    async def reserve(self, address: str):
        """Reserve a nonce using Redis distributed lock."""
        key = f"nonce:{address.lower()}"
        lock_key = f"{key}:lock"

        try:
            # Acquire distributed lock
            with self.redis.lock(
                lock_key,
                timeout=self.lock_timeout,
                blocking_timeout=self.blocking_timeout,
            ):
                # Get current on-chain nonce in executor to avoid blocking
                loop = asyncio.get_event_loop()
                onchain_nonce = await loop.run_in_executor(
                    self._executor,
                    self.web3.eth.get_transaction_count,
                    address,
                    "pending",
                )

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

                logger.debug(f"Reserved Redis nonce {next_nonce} for {address}")
                yield next_nonce

        except Exception as e:
            logger.error(f"Failed to reserve Redis nonce for {address}: {e}")
            raise RuntimeError(f"Redis nonce reservation failed for {address}: {e}")


class HybridNonceStore:
    """Hybrid nonce store with Redis primary and in-memory fallback."""

    def __init__(self, redis_client, web3_client):
        self.redis = redis_client
        self.web3 = web3_client
        self.redis_store = (
            RedisNonceStore(redis_client, web3_client) if redis_client else None
        )
        self.memory_store = InMemoryNonceStore()
        self._redis_healthy = True
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

    def _check_redis_health(self) -> bool:
        """Check if Redis is healthy."""
        if not self.redis:
            return False

        try:
            self.redis.ping()
            return True
        except Exception:
            return False

    @asynccontextmanager
    async def reserve(self, address: str):
        """Reserve nonce with fallback strategy."""
        # Check Redis health
        if self._redis_healthy and not self._check_redis_health():
            logger.warning("Redis unhealthy, switching to in-memory nonce store")
            self._redis_healthy = False

        if self._redis_healthy and self.redis_store:
            try:
                # Try Redis first
                async with self.redis_store.reserve(address) as nonce:
                    yield nonce
                return
            except Exception as e:
                logger.warning(
                    f"Redis nonce store failed: {e}, falling back to in-memory"
                )
                self._redis_healthy = False

        # Fallback to in-memory store
        try:
            async with self.memory_store.reserve(address) as nonce:
                # Sync with on-chain nonce to avoid conflicts
                loop = asyncio.get_event_loop()
                onchain_nonce = await loop.run_in_executor(
                    self._executor,
                    self.web3.eth.get_transaction_count,
                    address,
                    "pending",
                )
                if nonce <= onchain_nonce:
                    # Use on-chain nonce if it's higher
                    nonce = onchain_nonce + 1
                    logger.info(f"Synced in-memory nonce with on-chain: {nonce}")

                yield nonce
        except Exception as e:
            logger.error(f"Both Redis and in-memory nonce stores failed: {e}")
            raise RuntimeError(f"All nonce stores failed for {address}: {e}")
