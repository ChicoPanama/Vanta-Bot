"""
Copy execution mode management for safe testing and production rollouts
"""

import json
import os
import time
from enum import Enum
from typing import Any

from loguru import logger


class ExecutionMode(Enum):
    DRY = "DRY"
    LIVE = "LIVE"


class ExecutionModeManager:
    """Manages copy execution mode with runtime toggles and Redis persistence.

    Implements circuit breaker pattern for Redis failures:
    - On any Redis error, immediately fails safe to DRY mode
    - Requires N consecutive healthy reads before allowing LIVE mode
    - Tracks health streak to prevent flapping
    """

    def __init__(self, redis_client=None, consecutive_ok_required=3):
        # Initialize Redis client
        self.redis = redis_client
        self.consecutive_ok_required = consecutive_ok_required
        self._redis_health_streak = 0
        self._fallback_mode = ExecutionMode.DRY  # Always fail safe to DRY

        if self.redis is None:
            try:
                import redis

                from src.config.settings import settings

                self.redis = redis.from_url(settings.REDIS_URL)
                self.redis.ping()  # Test connection
                logger.info("Connected to Redis for execution mode persistence")
            except Exception as e:
                logger.warning(
                    f"Redis connection failed: {e}. Using in-memory mode only."
                )
                self.redis = None

        # Load initial state from environment
        env_mode = ExecutionMode(os.getenv("COPY_EXECUTION_MODE", "DRY"))
        env_emergency = os.getenv("EMERGENCY_STOP", "false").lower() == "true"

        # Try to load from Redis, fallback to environment
        self._mode = env_mode
        self._emergency_stop = env_emergency
        self._load_from_redis()

    @property
    def mode(self) -> ExecutionMode:
        """Get current execution mode"""
        return self._mode

    @property
    def is_dry_run(self) -> bool:
        """Check if currently in dry-run mode"""
        return self._mode == ExecutionMode.DRY

    @property
    def is_emergency_stopped(self) -> bool:
        """Check if emergency stop is active"""
        return self._emergency_stop

    def _load_from_redis(self) -> None:
        """Load execution mode from Redis with circuit breaker pattern.

        On any Redis error, fails safe to DRY mode and resets health streak.
        """
        if not self.redis:
            logger.debug("Redis not available, using fallback mode: DRY")
            self._mode = self._fallback_mode
            self._redis_health_streak = 0
            return

        try:
            mode_data = self.redis.get("exec_mode")
            if mode_data is None:
                logger.warning("Redis returned None for exec_mode, failing safe to DRY")
                self._mode = self._fallback_mode
                self._redis_health_streak = 0
                return

            data = json.loads(mode_data)
            requested_mode = ExecutionMode(data.get("mode", "DRY"))
            self._emergency_stop = data.get("emergency_stop", False)

            # Increment health streak on successful read
            self._redis_health_streak = min(self._redis_health_streak + 1, 999)

            # Only allow LIVE mode after consecutive healthy reads
            if requested_mode == ExecutionMode.LIVE:
                if self._redis_health_streak >= self.consecutive_ok_required:
                    self._mode = ExecutionMode.LIVE
                    logger.info(
                        "Loaded execution mode from Redis: LIVE (healthy streak: {})",
                        self._redis_health_streak,
                    )
                else:
                    self._mode = ExecutionMode.DRY
                    logger.warning(
                        "Redis requests LIVE but health streak insufficient ({}/{}), staying DRY",
                        self._redis_health_streak,
                        self.consecutive_ok_required,
                    )
            else:
                # DRY mode is always safe
                self._mode = ExecutionMode.DRY
                logger.info(
                    "Loaded execution mode from Redis: DRY (emergency: {})",
                    self._emergency_stop,
                )

        except Exception as e:
            logger.error(
                "Redis read failed, FAILING SAFE TO DRY MODE: {}", str(e), exc_info=True
            )
            self._mode = self._fallback_mode
            self._redis_health_streak = 0

    def _save_to_redis(self) -> None:
        """Save current execution mode to Redis."""
        if not self.redis:
            return

        try:
            data = {
                "mode": self._mode.value,
                "emergency_stop": self._emergency_stop,
                "updated_at": int(time.time()),
            }
            self.redis.set("exec_mode", json.dumps(data))
            logger.debug("Saved execution mode to Redis: {}", data)
        except Exception as e:
            logger.error(f"Failed to save execution mode to Redis: {e}")

    def set_mode(self, mode: ExecutionMode) -> None:
        """Set execution mode (for runtime toggling)"""
        old_mode = self._mode
        self._mode = mode
        self._save_to_redis()
        logger.info("Copy execution mode changed: {} -> {}", old_mode.value, mode.value)

    def set_emergency_stop(self, stop: bool) -> None:
        """Set emergency stop (for quick rollback)"""
        self._emergency_stop = stop
        self._save_to_redis()
        logger.warning(
            "Emergency stop {}: all copy execution disabled",
            "ACTIVATED" if stop else "DEACTIVATED",
        )

    def can_execute(self) -> bool:
        """Check if copy execution is allowed"""
        if self._emergency_stop:
            logger.debug("Copy execution blocked: emergency stop active")
            return False
        if self._mode == ExecutionMode.DRY:
            logger.debug("Copy execution blocked: DRY mode active")
            return False
        return True

    def get_execution_context(self) -> dict[str, Any]:
        """Get execution context for logging/auditing.

        This method refreshes from Redis with circuit breaker protection.
        On any Redis error, returns DRY mode.
        """
        # Refresh from Redis with circuit breaker
        self._load_from_redis()

        context = {
            "mode": self._mode.value,
            "emergency_stop": self._emergency_stop,
            "can_execute": self.can_execute(),
            "redis_connected": self.redis is not None,
            "redis_health_streak": self._redis_health_streak,
            "consecutive_ok_required": self.consecutive_ok_required,
        }

        # Add last update timestamp if available in Redis
        if self.redis and self._redis_health_streak > 0:
            try:
                mode_data = self.redis.get("exec_mode")
                if mode_data:
                    data = json.loads(mode_data)
                    context["last_updated"] = data.get("updated_at", 0)
            except Exception:
                # Don't fail, just skip timestamp
                logger.debug("Could not fetch last_updated timestamp from Redis")

        return context

    def refresh_from_redis(self) -> None:
        """Refresh execution mode from Redis with circuit breaker.

        On any Redis error, fails safe to DRY mode.
        """
        if not self.redis:
            self._mode = self._fallback_mode
            self._redis_health_streak = 0
            return

        # _load_from_redis already has circuit breaker logic
        self._load_from_redis()
        logger.debug(
            "Refreshed execution mode from Redis: {} (emergency: {}, streak: {})",
            self._mode.value,
            self._emergency_stop,
            self._redis_health_streak,
        )

    def get_health_metrics(self) -> dict[str, Any]:
        """Get health metrics for monitoring."""
        return {
            "execution_mode": self._mode.value,
            "emergency_stop": self._emergency_stop,
            "can_execute": self.can_execute(),
            "redis_persistence": self.redis is not None,
            "timestamp": int(time.time()),
        }


# Global instance
execution_manager = ExecutionModeManager()
