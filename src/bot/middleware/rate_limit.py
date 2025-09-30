"""Rate limiting middleware for bot commands."""

import logging
import time

from redis import Redis

from src.config.settings import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter using Redis."""

    def __init__(
        self, redis_client: Redis, capacity: int = 10, refill_per_sec: float = 1.0
    ):
        self.redis = redis_client
        self.capacity = capacity
        self.refill_per_sec = refill_per_sec

    def allow(self, user_id: int) -> bool:
        """Check if user is allowed to make a request.

        Args:
            user_id: User identifier

        Returns:
            True if allowed, False if rate limited
        """
        try:
            key = f"rate_limit:{user_id}"
            now = time.time()

            # Get current bucket state
            bucket_data = self.redis.hgetall(key)

            if not bucket_data:
                # Initialize bucket
                tokens = self.capacity - 1
                last_refill = now
            else:
                # Parse existing data
                tokens = float(bucket_data.get(b"tokens", self.capacity))
                last_refill = float(bucket_data.get(b"last_refill", now))

            # Calculate tokens to add based on time elapsed
            time_elapsed = now - last_refill
            tokens_to_add = time_elapsed * self.refill_per_sec
            tokens = min(self.capacity, tokens + tokens_to_add)

            if tokens >= 1:
                # Consume one token
                tokens -= 1
                self.redis.hmset(key, {"tokens": tokens, "last_refill": now})
                self.redis.expire(key, 3600)  # Expire after 1 hour
                return True
            else:
                # Rate limited
                self.redis.hmset(key, {"tokens": tokens, "last_refill": now})
                self.redis.expire(key, 3600)
                return False

        except Exception as e:
            logger.error(f"Rate limiter error for user {user_id}: {e}")
            # Allow on error to avoid blocking users
            return True

    def get_remaining_tokens(self, user_id: int) -> int:
        """Get remaining tokens for user.

        Args:
            user_id: User identifier

        Returns:
            Number of remaining tokens
        """
        try:
            key = f"rate_limit:{user_id}"
            bucket_data = self.redis.hgetall(key)

            if not bucket_data:
                return self.capacity

            tokens = float(bucket_data.get(b"tokens", self.capacity))
            last_refill = float(bucket_data.get(b"last_refill", time.time()))

            # Calculate current tokens
            now = time.time()
            time_elapsed = now - last_refill
            tokens_to_add = time_elapsed * self.refill_per_sec
            current_tokens = min(self.capacity, tokens + tokens_to_add)

            return int(current_tokens)

        except Exception as e:
            logger.error(f"Failed to get remaining tokens for user {user_id}: {e}")
            return self.capacity

    def reset(self, user_id: int):
        """Reset rate limit for user.

        Args:
            user_id: User identifier
        """
        try:
            key = f"rate_limit:{user_id}"
            self.redis.delete(key)
            logger.info(f"Reset rate limit for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to reset rate limit for user {user_id}: {e}")


class CommandRateLimiter:
    """Rate limiter for specific bot commands."""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.limiters = {
            "trade": RateLimiter(
                redis_client, capacity=5, refill_per_sec=0.5
            ),  # 5 trades per 10 seconds
            "status": RateLimiter(
                redis_client, capacity=20, refill_per_sec=2.0
            ),  # 20 status checks per 10 seconds
            "help": RateLimiter(
                redis_client, capacity=10, refill_per_sec=1.0
            ),  # 10 help requests per 10 seconds
            "default": RateLimiter(
                redis_client, capacity=10, refill_per_sec=1.0
            ),  # Default rate limit
        }

    def allow_command(self, user_id: int, command: str) -> bool:
        """Check if user can execute command.

        Args:
            user_id: User identifier
            command: Command name

        Returns:
            True if allowed, False if rate limited
        """
        try:
            # Get appropriate limiter
            limiter = self.limiters.get(command, self.limiters["default"])

            # Check rate limit
            allowed = limiter.allow(user_id)

            if not allowed:
                logger.warning(f"Rate limited user {user_id} for command {command}")
                return False

            return True

        except Exception as e:
            logger.error(
                f"Command rate limiter error for user {user_id}, command {command}: {e}"
            )
            # Allow on error
            return True

    def get_command_limits(self, user_id: int) -> dict:
        """Get rate limit status for all commands.

        Args:
            user_id: User identifier

        Returns:
            Dict mapping command to remaining tokens
        """
        limits = {}
        for command, limiter in self.limiters.items():
            limits[command] = limiter.get_remaining_tokens(user_id)
        return limits

    def reset_user_limits(self, user_id: int):
        """Reset all rate limits for user.

        Args:
            user_id: User identifier
        """
        for limiter in self.limiters.values():
            limiter.reset(user_id)
        logger.info(f"Reset all rate limits for user {user_id}")


# Global rate limiter instance
def create_rate_limiter() -> CommandRateLimiter:
    """Create rate limiter instance."""
    try:
        import redis

        redis_client = redis.from_url(settings.REDIS_URL)
        return CommandRateLimiter(redis_client)
    except Exception as e:
        logger.error(f"Failed to create rate limiter: {e}")
        # Return dummy limiter that always allows
        return CommandRateLimiter(None)
