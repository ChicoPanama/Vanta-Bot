"""
Feature Flags System
Runtime configuration and feature toggles for the Vanta Bot
"""

import os
from enum import Enum
from typing import Any

from src.config.settings import settings


class ExecutionMode(Enum):
    """Copy trading execution modes"""

    DRY = "DRY"
    LIVE = "LIVE"


class FeatureFlags:
    """Feature flags and runtime configuration"""

    def __init__(self):
        self._flags: dict[str, Any] = {}
        self._load_flags()

    def _load_flags(self) -> None:
        """Load feature flags from environment variables"""
        # Execution mode
        self._flags["execution_mode"] = ExecutionMode(
            os.getenv("COPY_EXECUTION_MODE", "DRY").upper()
        )

        # Emergency controls
        self._flags["emergency_stop"] = (
            os.getenv("EMERGENCY_STOP", "false").lower() == "true"
        )
        self._flags["emergency_stop_copy_trading"] = (
            os.getenv("EMERGENCY_STOP_COPY_TRADING", "false").lower() == "true"
        )
        self._flags["pause_new_follows"] = (
            os.getenv("PAUSE_NEW_FOLLOWS", "false").lower() == "true"
        )
        self._flags["maintenance_mode"] = (
            os.getenv("MAINTENANCE_MODE", "false").lower() == "true"
        )

        # Feature toggles
        self._flags["enable_copy_trading"] = (
            os.getenv("ENABLE_COPY_TRADING", "true").lower() == "true"
        )
        self._flags["enable_ai_analysis"] = (
            os.getenv("ENABLE_AI_ANALYSIS", "true").lower() == "true"
        )
        self._flags["enable_market_intelligence"] = (
            os.getenv("ENABLE_MARKET_INTELLIGENCE", "true").lower() == "true"
        )
        self._flags["enable_leaderboard"] = (
            os.getenv("ENABLE_LEADERBOARD", "true").lower() == "true"
        )
        self._flags["enable_telegram_commands"] = (
            os.getenv("ENABLE_TELEGRAM_COMMANDS", "true").lower() == "true"
        )

        # Trading features
        self._flags["enable_market_orders"] = (
            os.getenv("ENABLE_MARKET_ORDERS", "true").lower() == "true"
        )
        self._flags["enable_limit_orders"] = (
            os.getenv("ENABLE_LIMIT_ORDERS", "false").lower() == "true"
        )
        self._flags["enable_stop_orders"] = (
            os.getenv("ENABLE_STOP_ORDERS", "false").lower() == "true"
        )

        # Risk management
        self._flags["enable_slippage_protection"] = (
            os.getenv("ENABLE_SLIPPAGE_PROTECTION", "true").lower() == "true"
        )
        self._flags["enable_position_limits"] = (
            os.getenv("ENABLE_POSITION_LIMITS", "true").lower() == "true"
        )
        self._flags["enable_leverage_limits"] = (
            os.getenv("ENABLE_LEVERAGE_LIMITS", "true").lower() == "true"
        )

        # Monitoring and observability
        self._flags["enable_metrics"] = (
            os.getenv("ENABLE_METRICS", "true").lower() == "true"
        )
        self._flags["enable_health_checks"] = (
            os.getenv("ENABLE_HEALTH_CHECKS", "true").lower() == "true"
        )
        self._flags["enable_performance_logging"] = (
            os.getenv("ENABLE_PERFORMANCE_LOGGING", "true").lower() == "true"
        )

        # External integrations
        self._flags["enable_price_feeds"] = (
            os.getenv("ENABLE_PRICE_FEEDS", "true").lower() == "true"
        )
        self._flags["enable_avantis_sdk"] = (
            os.getenv("ENABLE_AVANTIS_SDK", "true").lower() == "true"
        )
        self._flags["enable_pyth_feeds"] = (
            os.getenv("ENABLE_PYTH_FEEDS", "true").lower() == "true"
        )

        # Development and debugging
        self._flags["enable_debug_mode"] = settings.DEBUG
        self._flags["enable_detailed_logging"] = (
            os.getenv("ENABLE_DETAILED_LOGGING", "false").lower() == "true"
        )
        self._flags["enable_test_mode"] = (
            os.getenv("ENABLE_TEST_MODE", "false").lower() == "true"
        )

    def execution_mode(self) -> ExecutionMode:
        """Get current execution mode"""
        return self._flags["execution_mode"]

    def is_dry_mode(self) -> bool:
        """Check if running in dry mode"""
        return self._flags["execution_mode"] == ExecutionMode.DRY

    def is_live_mode(self) -> bool:
        """Check if running in live mode"""
        return self._flags["execution_mode"] == ExecutionMode.LIVE

    def is_emergency_stopped(self) -> bool:
        """Check if system is in emergency stop"""
        return self._flags["emergency_stop"]

    def is_copy_trading_stopped(self) -> bool:
        """Check if copy trading is stopped"""
        return self._flags["emergency_stop_copy_trading"]

    def is_maintenance_mode(self) -> bool:
        """Check if system is in maintenance mode"""
        return self._flags["maintenance_mode"]

    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled"""
        return self._flags.get(feature, False)

    def can_execute_trades(self) -> bool:
        """Check if trade execution is allowed"""
        return (
            not self._flags["emergency_stop"]
            and not self._flags["maintenance_mode"]
            and self._flags["enable_copy_trading"]
            and self._flags["enable_market_orders"]
        )

    def can_copy_trade(self) -> bool:
        """Check if copy trading is allowed"""
        return (
            not self._flags["emergency_stop"]
            and not self._flags["emergency_stop_copy_trading"]
            and not self._flags["maintenance_mode"]
            and not self._flags["pause_new_follows"]
            and self._flags["enable_copy_trading"]
        )

    def can_follow_new_leaders(self) -> bool:
        """Check if new leader follows are allowed"""
        return (
            not self._flags["emergency_stop"]
            and not self._flags["pause_new_follows"]
            and not self._flags["maintenance_mode"]
            and self._flags["enable_copy_trading"]
        )

    def can_use_ai_features(self) -> bool:
        """Check if AI features are available"""
        return (
            not self._flags["maintenance_mode"]
            and self._flags["enable_ai_analysis"]
            and self._flags["enable_market_intelligence"]
        )

    def can_show_leaderboard(self) -> bool:
        """Check if leaderboard can be shown"""
        return not self._flags["maintenance_mode"] and self._flags["enable_leaderboard"]

    def can_process_telegram_commands(self) -> bool:
        """Check if Telegram commands can be processed"""
        return (
            not self._flags["maintenance_mode"]
            and self._flags["enable_telegram_commands"]
        )

    def get_slippage_tolerance(self) -> float:
        """Get slippage tolerance based on mode"""
        if self.is_dry_mode():
            return 5.0  # Higher tolerance in dry mode
        else:
            env_value = os.getenv("DEFAULT_SLIPPAGE_PCT")
            if env_value is not None:
                try:
                    return float(env_value)
                except ValueError:
                    pass
            return settings.DEFAULT_SLIPPAGE_PCT

    def get_max_leverage(self) -> int:
        """Get maximum leverage based on mode and flags"""
        if not self._flags["enable_leverage_limits"]:
            return settings.MAX_LEVERAGE

        if self.is_dry_mode():
            return min(settings.MAX_LEVERAGE, 100)  # Lower limit in dry mode
        else:
            env_limit = os.getenv("MAX_COPY_LEVERAGE")
            if env_limit is not None:
                try:
                    return int(env_limit)
                except ValueError:
                    pass
            return settings.MAX_COPY_LEVERAGE

    def get_position_limits(self) -> tuple[int, int]:
        """Get position size limits"""
        if not self._flags["enable_position_limits"]:
            return (0, settings.MAX_POSITION_SIZE)

        if self.is_dry_mode():
            return (settings.MIN_POSITION_SIZE, min(settings.MAX_POSITION_SIZE, 1000))
        else:
            return (settings.MIN_POSITION_SIZE, settings.MAX_POSITION_SIZE)

    def get_all_flags(self) -> dict[str, Any]:
        """Get all feature flags (for debugging)"""
        return self._flags.copy()

    def set_flag(self, flag_name: str, value: Any) -> None:
        """Set a feature flag value (for runtime configuration)"""
        self._flags[flag_name] = value

    def get_status_summary(self) -> str:
        """Get human-readable status summary"""
        mode = "🔍 DRY" if self.is_dry_mode() else "⚠️ LIVE"
        emergency = "🚨 EMERGENCY STOP" if self.is_emergency_stopped() else "✅ RUNNING"
        maintenance = "🔧 MAINTENANCE" if self.is_maintenance_mode() else "✅ OPERATIONAL"

        return f"""
Feature Flags Status:
- Execution Mode: {mode}
- System Status: {emergency}
- Maintenance: {maintenance}
- Copy Trading: {"✅ ENABLED" if self.can_copy_trade() else "❌ DISABLED"}
- AI Features: {"✅ ENABLED" if self.can_use_ai_features() else "❌ DISABLED"}
- Leaderboard: {"✅ ENABLED" if self.can_show_leaderboard() else "❌ DISABLED"}
- Telegram Commands: {"✅ ENABLED" if self.can_process_telegram_commands() else "❌ DISABLED"}
        """.strip()


# Global feature flags instance
flags = FeatureFlags()
