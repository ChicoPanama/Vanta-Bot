"""
Vanta Bot - Main Entry Point
Professional Telegram trading bot for the Avantis Protocol on Base network
"""

import asyncio
import sys
from typing import Optional

from src.config.settings import settings
from src.config.flags import flags
from src.utils.logging import get_logger, setup_logging
from src.utils.errors import handle_exception
from src.bot.application import create_bot_application
from src.services.background import BackgroundServiceManager

# Setup logging first
setup_logging()
logger = get_logger(__name__)


async def start_background_services() -> None:
    """Start background services"""
    try:
        background_manager = BackgroundServiceManager()
        await background_manager.start_all_services()
        logger.info("✅ Background services started successfully")
    except Exception as e:
        logger.error(f"❌ Error starting background services: {e}")
        raise





def main():
    """Start the bot"""
    try:
        # Log startup information
        logger.info("🚀 Starting Vanta Bot with Advanced Features...")
        logger.info(settings.runtime_summary())
        logger.info(flags.get_status_summary())
        
        # Create application
        app = create_bot_application()
        
        # Start background services
        asyncio.create_task(start_background_services())
        
        logger.info("✅ Vanta Bot started successfully")
        app.run_polling()
        
    except Exception as e:
        error = handle_exception(e, {"operation": "main"})
        logger.error(f"❌ Failed to start bot: {error.message}")
        sys.exit(1)


if __name__ == "__main__":
    main()