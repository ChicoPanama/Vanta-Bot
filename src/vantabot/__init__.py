"""Vanta Bot - Professional Telegram trading bot for Avantis Protocol on Base network."""

__version__ = "2.1.0"
__author__ = "Avantis Trading Team"
__email__ = "dev@avantis.trading"

from .app import create_app

__all__ = ["create_app", "__version__"]
