"""
Vanta Bot - Professional Trading Bot for Avantis Protocol

A comprehensive, production-ready Telegram trading bot for the Avantis Protocol 
on Base network, featuring advanced trading capabilities, AI-powered copy trading, 
and enterprise-grade architecture.
"""

import importlib.metadata

try:
    __version__ = importlib.metadata.version("avantis-telegram-bot")
except importlib.metadata.PackageNotFoundError:  # pragma: no cover - fallback for local execution
    __version__ = "0.0.0-dev"
__author__ = "Vanta Bot Team"
__email__ = "support@vanta-bot.com"
__description__ = "Professional Trading Bot for Avantis Protocol on Base network"

# Export main components
try:
    from src.config.settings import settings  # type: ignore
except Exception:  # pragma: no cover - optional during lightweight imports
    settings = None

try:
    from src.config.flags import flags  # type: ignore
except Exception:  # pragma: no cover - optional during lightweight imports
    flags = None

try:
    from src.utils.logging import get_logger
except Exception:  # pragma: no cover - fallback logger accessor
    import logging

    def get_logger(name: str):  # type: ignore
        return logging.getLogger(name)

from src.utils.errors import AppError, ValidationError, ExternalAPIError

__all__ = [
    "__version__",
    "__author__", 
    "__email__",
    "__description__",
    "settings",
    "flags",
    "get_logger",
    "AppError",
    "ValidationError", 
    "ExternalAPIError",
]
