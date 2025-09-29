"""Vanta Bot CLI entrypoint."""

from __future__ import annotations

import asyncio
import sys

from src.utils.errors import handle_exception
from src.utils.logging import get_logger
from .app import create_app

logger = get_logger(__name__)


def main() -> None:
    """Program entry point."""
    try:
        app = create_app()
        asyncio.run(app.run())
    except KeyboardInterrupt:
        logger.info("🛑 Shutdown requested by user")
    except Exception as exc:  # noqa: BLE001
        error = handle_exception(exc, {"operation": "main"})
        logger.error(f"❌ Failed to start bot: {error.message}")
        sys.exit(1)


if __name__ == "__main__":
    main()
