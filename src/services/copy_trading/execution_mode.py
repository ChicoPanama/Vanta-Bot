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
    """Manages copy execution mode with runtime toggles and Redis persistence"""

    def __init__(self, redis_client=None):
        # Initialize Redis client
        self.redis = redis_client
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
        """Load execution mode from Redis on startup."""
        if not self.redis:
            return

        try:
            mode_data = self.redis.get("exec_mode")
            if mode_data:
                data = json.loads(mode_data)
                self._mode = ExecutionMode(data.get("mode", "DRY"))
                self._emergency_stop = data.get("emergency_stop", False)
                logger.info(
                    "Loaded execution mode from Redis: {} (emergency: {})",
                    self._mode.value,
                    self._emergency_stop,
                )
        except Exception as e:
            logger.warning(f"Failed to load execution mode from Redis: {e}")

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
        """Get execution context for logging/auditing"""
        context = {
            "mode": self._mode.value,
            "emergency_stop": self._emergency_stop,
            "can_execute": self.can_execute(),
            "redis_connected": self.redis is not None,
        }

        # Add last update timestamp if available in Redis
        if self.redis:
            try:
                mode_data = self.redis.get("exec_mode")
                if mode_data:
                    data = json.loads(mode_data)
                    context["last_updated"] = data.get("updated_at", 0)
            except Exception:
                pass

        return context

    def refresh_from_redis(self) -> None:
        """Refresh execution mode from Redis (for multi-process coordination)."""
        if not self.redis:
            return
        try:
            self._load_from_redis()
            logger.debug(
                "Refreshed execution mode from Redis: {} (emergency: {})",
                self._mode.value,
                self._emergency_stop,
            )
        except Exception as e:
            logger.warning(f"Failed to refresh execution mode from Redis: {e}")

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
