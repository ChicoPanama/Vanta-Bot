"""
Rate Limiting with Redis
Comprehensive rate limiting for trading operations and user interactions
"""

import aioredis
import time
import os
import logging
from typing import Optional, Dict, Any
from decimal import Decimal

from src.config.settings import settings
from src.utils.logging import get_logger, set_trace_id

log = get_logger(__name__)


class RateLimitError(Exception):
    def __init__(self, limit_type: str, retry_after: int):
        self.limit_type = limit_type
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded for {limit_type}. Retry after {retry_after}s")


class RateLimiter:
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self._redis: Optional[aioredis.Redis] = None
        
    async def get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = await aioredis.from_url(self.redis_url)
        return self._redis
    
    async def check_limit(
        self, 
        user_id: str, 
        action: str, 
        limit: int, 
        window: int
    ) -> bool:
        """Check if action is within rate limit."""
        redis = await self.get_redis()
        now = int(time.time())
        key = f"rate_limit:{action}:{user_id}:{now // window}"
        
        current = await redis.incr(key)
        if current == 1:
            await redis.expire(key, window)
            
        return current <= limit
    
    async def check_trading_limits(self, user_id: str) -> Dict[str, Any]:
        """Check comprehensive trading limits for a user."""
        limits = {
            'open_positions': {'limit': 5, 'window': 60, 'passed': False},
            'daily_trades': {'limit': 50, 'window': 86400, 'passed': False},
            'hourly_volume': {'limit': 10000, 'window': 3600, 'passed': False}  # $10k/hour
        }
        
        results = {}
        for limit_type, config in limits.items():
            passed = await self.check_limit(
                user_id, 
                limit_type, 
                config['limit'], 
                config['window']
            )
            
            results[limit_type] = {
                **config,
                'passed': passed,
                'retry_after': config['window'] if not passed else 0
            }
            
            if not passed:
                raise RateLimitError(limit_type, config['window'])
        
        return results
    
    async def track_volume(self, user_id: str, volume_usd: Decimal):
        """Track trading volume for volume-based limits."""
        redis = await self.get_redis()
        now = int(time.time())
        
        # Track hourly volume
        hourly_key = f"volume:hourly:{user_id}:{now // 3600}"
        await redis.incrbyfloat(hourly_key, float(volume_usd))
        await redis.expire(hourly_key, 3600)
        
        # Track daily volume
        daily_key = f"volume:daily:{user_id}:{now // 86400}"
        await redis.incrbyfloat(daily_key, float(volume_usd))
        await redis.expire(daily_key, 86400)
        
    async def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get current usage stats for a user."""
        redis = await self.get_redis()
        now = int(time.time())
        
        # Get current counts
        hourly_trades = await redis.get(f"rate_limit:open_positions:{user_id}:{now // 60}")
        daily_trades = await redis.get(f"rate_limit:daily_trades:{user_id}:{now // 86400}")
        hourly_volume = await redis.get(f"volume:hourly:{user_id}:{now // 3600}")
        daily_volume = await redis.get(f"volume:daily:{user_id}:{now // 86400}")
        
        return {
            'hourly_trades': int(hourly_trades or 0),
            'daily_trades': int(daily_trades or 0),
            'hourly_volume_usd': float(hourly_volume or 0),
            'daily_volume_usd': float(daily_volume or 0),
            'timestamp': now
        }
    
    async def check_telegram_limits(self, user_id: str) -> bool:
        """Check Telegram message rate limits."""
        limit = settings.TELEGRAM_MESSAGE_RATE_LIMIT
        window = 60  # 1 minute
        
        return await self.check_limit(
            user_id,
            'telegram_messages',
            limit,
            window
        )
    
    async def check_copy_trading_limits(self, user_id: str) -> bool:
        """Check copy trading execution limits."""
        limit = settings.COPY_EXECUTION_RATE_LIMIT
        window = 60  # 1 minute
        
        return await self.check_limit(
            user_id,
            'copy_executions',
            limit,
            window
        )
    
    async def track_trade_execution(self, user_id: str, volume_usd: Decimal):
        """Track a trade execution for rate limiting."""
        # Increment trade counters
        redis = await self.get_redis()
        now = int(time.time())
        
        # Daily trades
        daily_key = f"rate_limit:daily_trades:{user_id}:{now // 86400}"
        await redis.incr(daily_key)
        await redis.expire(daily_key, 86400)
        
        # Open positions (simplified - in real implementation, track actual positions)
        positions_key = f"rate_limit:open_positions:{user_id}:{now // 60}"
        await redis.incr(positions_key)
        await redis.expire(positions_key, 60)
        
        # Track volume
        await self.track_volume(user_id, volume_usd)
    
    async def cleanup_expired_entries(self):
        """Clean up expired rate limit entries (maintenance task)."""
        redis = await self.get_redis()
        now = int(time.time())
        
        # This would be implemented based on Redis key patterns
        # For now, Redis TTL handles expiration automatically
        log.debug("Rate limit cleanup completed")
    
    async def get_rate_limit_status(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive rate limit status for a user."""
        try:
            stats = await self.get_user_stats(user_id)
            
            # Check current limits
            telegram_ok = await self.check_telegram_limits(user_id)
            copy_ok = await self.check_copy_trading_limits(user_id)
            
            return {
                'user_id': user_id,
                'stats': stats,
                'limits': {
                    'telegram_messages': {
                        'passed': telegram_ok,
                        'limit': settings.TELEGRAM_MESSAGE_RATE_LIMIT,
                        'window': 60
                    },
                    'copy_executions': {
                        'passed': copy_ok,
                        'limit': settings.COPY_EXECUTION_RATE_LIMIT,
                        'window': 60
                    },
                    'daily_trades': {
                        'current': stats['daily_trades'],
                        'limit': 50
                    },
                    'hourly_volume': {
                        'current': stats['hourly_volume_usd'],
                        'limit': 10000
                    }
                },
                'timestamp': time.time()
            }
        except Exception as e:
            log.error(f"Error getting rate limit status for user {user_id}: {e}")
            return {
                'user_id': user_id,
                'error': str(e),
                'timestamp': time.time()
            }


# Global rate limiter instance
rate_limiter = RateLimiter()