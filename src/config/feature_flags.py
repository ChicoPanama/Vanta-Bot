"""
Feature flags for copy-trading rollout and control
"""

import os


def is_autocopy_allowed(user_id: int) -> bool:
    """
    Check if auto-copy is allowed for a specific user.

    Returns True if:
    1. User is in the AUTOCOPY_ALLOWLIST, OR
    2. COPY_AUTOCOPY_DEFAULT is set to "on" (and user is not explicitly blocked)

    Returns False if:
    1. User is not in allowlist AND COPY_AUTOCOPY_DEFAULT is "off"
    """
    # Get allowlist from environment
    allowlist_str = os.getenv("AUTOCOPY_ALLOWLIST", "")
    allowlist = set()

    if allowlist_str:
        for user_str in allowlist_str.split(","):
            user_str = user_str.strip()
            if user_str:
                try:
                    allowlist.add(int(user_str))
                except ValueError:
                    continue  # Skip invalid user IDs

    # Check if user is in allowlist
    if user_id in allowlist:
        return True

    # Check default setting
    default_setting = os.getenv("COPY_AUTOCOPY_DEFAULT", "off").lower()
    return default_setting == "on"


def get_autocopy_default() -> bool:
    """Get the default auto-copy setting"""
    default_setting = os.getenv("COPY_AUTOCOPY_DEFAULT", "off").lower()
    return default_setting == "on"


def get_autocopy_allowlist() -> set[int]:
    """Get the set of allowed user IDs"""
    allowlist_str = os.getenv("AUTOCOPY_ALLOWLIST", "")
    allowlist = set()

    if allowlist_str:
        for user_str in allowlist_str.split(","):
            user_str = user_str.strip()
            if user_str:
                try:
                    allowlist.add(int(user_str))
                except ValueError:
                    continue  # Skip invalid user IDs

    return allowlist


def is_feature_enabled(feature_name: str, default: bool = False) -> bool:
    """
    Generic feature flag checker.

    Args:
        feature_name: Name of the feature (e.g., "COPY_TRADING", "DAILY_DIGEST")
        default: Default value if feature flag is not set

    Returns:
        True if feature is enabled, False otherwise
    """
    env_var = f"FEATURE_{feature_name.upper()}"
    value = os.getenv(env_var, "").lower()

    if value in ("true", "1", "on", "yes"):
        return True
    elif value in ("false", "0", "off", "no"):
        return False
    else:
        return default


# Common feature flags
def is_copy_trading_enabled() -> bool:
    """Check if copy-trading feature is enabled"""
    return is_feature_enabled("COPY_TRADING", True)  # Default to enabled


def is_daily_digest_enabled() -> bool:
    """Check if daily digest feature is enabled"""
    return is_feature_enabled("DAILY_DIGEST", True)  # Default to enabled


def is_synthetic_signals_enabled() -> bool:
    """Check if synthetic signals are enabled"""
    return is_feature_enabled("SYNTHETIC_SIGNALS", True)  # Default to enabled
