"""
Cache Service
Redis-based caching for improved performance
"""

import asyncio
import json
from functools import wraps
from typing import Any, Optional

import redis.asyncio as redis

from src.config.settings import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class CacheService:
    """Redis-based caching service"""

    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self._connection_pool: Optional[redis.ConnectionPool] = None

    async def initialize(self) -> None:
        """Initialize Redis connection"""
        try:
            self._connection_pool = redis.ConnectionPool.from_url(
                settings.REDIS_URL, max_connections=20, retry_on_timeout=True
            )
            self.redis = redis.Redis(connection_pool=self._connection_pool)

            # Test connection
            await self.redis.ping()
            logger.info("✅ Cache service initialized successfully")

        except Exception as e:
            logger.error(f"❌ Failed to initialize cache service: {e}")
            self.redis = None

    async def close(self) -> None:
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
        if self._connection_pool:
            await self._connection_pool.disconnect()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis:
            return None

        try:
            value = await self.redis.get(key)
            if value:
                # FIX: Replace unsafe pickle with safe JSON serialization
                # REASON: pickle.loads() can execute arbitrary code - security vulnerability
                # REVIEW: Line 60 from code review - pickle load (unsafe with untrusted data)
                return json.loads(value.decode("utf-8"))
            return None
        except Exception as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL"""
        if not self.redis:
            return False

        try:
            # FIX: Replace unsafe pickle with safe JSON serialization
            # REASON: pickle.dumps() can serialize unsafe objects - security vulnerability
            # REVIEW: Line 75 from code review - pickle dumps (unsafe with untrusted data)
            serialized_value = json.dumps(value, default=str).encode("utf-8")

            if ttl:
                await self.redis.setex(key, ttl, serialized_value)
            else:
                await self.redis.set(key, serialized_value)

            return True
        except Exception as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.redis:
            return False

        try:
            result = await self.redis.delete(key)
            return result > 0
        except Exception as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.redis:
            return False

        try:
            result = await self.redis.exists(key)
            return result > 0
        except Exception as e:
            logger.warning(f"Cache exists error for key {key}: {e}")
            return False

    async def get_or_set(
        self, key: str, factory_func, ttl: Optional[int] = None
    ) -> Any:
        """Get value from cache or set it using factory function"""
        value = await self.get(key)

        if value is None:
            try:
                value = (
                    await factory_func()
                    if asyncio.iscoroutinefunction(factory_func)
                    else factory_func()
                )
                await self.set(key, value, ttl)
            except Exception as e:
                logger.error(f"Factory function error for key {key}: {e}")
                raise

        return value

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern"""
        if not self.redis:
            return 0

        try:
            keys = await self.redis.keys(pattern)
            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Cache pattern invalidation error for {pattern}: {e}")
            return 0


# Global cache service instance
cache_service = CacheService()


def cached(ttl: int = 300, key_prefix: str = ""):
    """Decorator for caching function results"""

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"

            # Try to get from cache
            cached_result = await cache_service.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_service.set(cache_key, result, ttl)

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"

            # For sync functions, we'll need to run in event loop
            loop = asyncio.get_event_loop()

            # Try to get from cache
            cached_result = loop.run_until_complete(cache_service.get(cache_key))
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = func(*args, **kwargs)
            loop.run_until_complete(cache_service.set(cache_key, result, ttl))

            return result

        # Return appropriate wrapper based on function type
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


# Cache key generators
class CacheKeys:
    """Cache key constants"""

    USER_STATS = "user_stats:{user_id}"
    PORTFOLIO_SUMMARY = "portfolio_summary:{user_id}"
    PRICE_DATA = "price_data:{symbol}"
    POSITIONS = "positions:{user_id}:{status}"
    LEADERBOARD = "leaderboard:{timeframe}"
    ANALYTICS = "analytics:{user_id}:{metric}"

    @staticmethod
    def user_stats(user_id: int) -> str:
        return CacheKeys.USER_STATS.format(user_id=user_id)

    @staticmethod
    def portfolio_summary(user_id: int) -> str:
        return CacheKeys.PORTFOLIO_SUMMARY.format(user_id=user_id)

    @staticmethod
    def price_data(symbol: str) -> str:
        return CacheKeys.PRICE_DATA.format(symbol=symbol)

    @staticmethod
    def positions(user_id: int, status: str) -> str:
        return CacheKeys.POSITIONS.format(user_id=user_id, status=status)

    @staticmethod
    def leaderboard(timeframe: str) -> str:
        return CacheKeys.LEADERBOARD.format(timeframe=timeframe)

    @staticmethod
    def analytics(user_id: int, metric: str) -> str:
        return CacheKeys.ANALYTICS.format(user_id=user_id, metric=metric)
