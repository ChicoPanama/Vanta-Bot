"""
Vanta Bot - Professional Trading Bot for Avantis Protocol

A comprehensive, production-ready Telegram trading bot for the Avantis Protocol 
on Base network, featuring advanced trading capabilities, AI-powered copy trading, 
and enterprise-grade architecture.
"""

import importlib.metadata

__version__ = importlib.metadata.version("avantis-telegram-bot")
__author__ = "Vanta Bot Team"
__email__ = "support@vanta-bot.com"
__description__ = "Professional Trading Bot for Avantis Protocol on Base network"

# Export main components
from src.config.settings import settings
from src.config.flags import flags
from src.utils.logging import get_logger
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
