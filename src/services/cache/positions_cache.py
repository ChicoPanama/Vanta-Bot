"""Lightweight positions cache using Redis (Phase 4)."""

import json
import logging
from typing import Optional

import redis

from src.config.settings import settings

logger = logging.getLogger(__name__)


class PositionsCache:
    """Redis cache for user positions."""

    def __init__(self):
        """Initialize Redis client."""
        try:
            self.r = redis.from_url(settings.REDIS_URL, decode_responses=True)
            # Test connection
            self.r.ping()
        except Exception as e:
            logger.warning(f"Redis not available, cache disabled: {e}")
            self.r = None

    def _key(self, user_addr: str) -> str:
        """Generate cache key for user positions.

        Args:
            user_addr: User wallet address

        Returns:
            Redis key
        """
        chain_id = getattr(settings, "CHAIN_ID", 8453)  # Base mainnet
        return f"pos:{chain_id}:{user_addr.lower()}"

    def set_positions(
        self, user_addr: str, positions: list[dict], ttl: int = 30
    ) -> None:
        """Cache user positions.

        Args:
            user_addr: User wallet address
            positions: List of position dicts
            ttl: Time-to-live in seconds (default 30s)
        """
        if not self.r:
            return

        try:
            key = self._key(user_addr)
            self.r.setex(key, ttl, json.dumps(positions))
            logger.debug(f"Cached {len(positions)} positions for {user_addr[:8]}...")
        except Exception as e:
            logger.warning(f"Failed to cache positions: {e}")

    def get_positions(self, user_addr: str) -> Optional[list[dict]]:
        """Get cached user positions.

        Args:
            user_addr: User wallet address

        Returns:
            List of position dicts, or None if not cached
        """
        if not self.r:
            return None

        try:
            key = self._key(user_addr)
            raw = self.r.get(key)
            if raw:
                logger.debug(f"Cache hit for {user_addr[:8]}...")
                return json.loads(raw)
            return None
        except Exception as e:
            logger.warning(f"Failed to get cached positions: {e}")
            return None

    def invalidate(self, user_addr: str) -> None:
        """Invalidate cached positions for a user.

        Args:
            user_addr: User wallet address
        """
        if not self.r:
            return

        try:
            key = self._key(user_addr)
            self.r.delete(key)
            logger.debug(f"Invalidated cache for {user_addr[:8]}...")
        except Exception as e:
            logger.warning(f"Failed to invalidate cache: {e}")
