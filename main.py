"""
Vanta Bot - Main Entry Point
Professional Telegram trading bot for the Avantis Protocol on Base network
"""

import asyncio
import sys
from typing import Optional

from src.config.settings import settings
from src.config.flags import flags
from src.utils.logging import get_logger, setup_logging, set_trace_id
from src.utils.errors import handle_exception
from src.bot.application import create_bot_application
from src.services.background import BackgroundServiceManager
from src.utils.supervisor import TaskManager
from src.monitoring.health_server import start_health_server, HealthChecker

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


async def start_production_services() -> None:
    """Start production-ready services with supervision"""
    trace_id = set_trace_id()
    logger.info("🚀 Starting production services with supervision", extra={'trace_id': trace_id})
    
    try:
        # Initialize health checker
        health_checker = HealthChecker()
        
        # Start health server
        health_runner = await start_health_server(health_checker)
        
        # Initialize task manager for supervised tasks
        task_manager = TaskManager()
        task_manager.setup_signal_handlers()
        
        # Add supervised tasks for critical services
        task_manager.add_task(
            lambda: background_manager.start_all_services(),
            "background.services",
            base_delay=2.0,
            max_delay=30.0
        )
        
        # Start all supervised tasks
        await task_manager.start_all()
        
        logger.info("✅ Production services started successfully", extra={'trace_id': trace_id})
        
        # Keep running until shutdown
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("🛑 Shutdown signal received", extra={'trace_id': trace_id})
            await task_manager.shutdown_all()
            await health_runner.cleanup()
            
    except Exception as e:
        logger.error(f"❌ Error starting production services: {e}", extra={'trace_id': trace_id})
        raise





def main():
    """Start the bot"""
    try:
        # Log startup information
        trace_id = set_trace_id()
        logger.info("🚀 Starting Vanta Bot with Production Hardening...", extra={'trace_id': trace_id})
        logger.info(settings.runtime_summary())
        logger.info(flags.get_status_summary())
        
        # Check if running in production mode
        if settings.is_production():
            logger.info("🏭 Production mode detected - starting supervised services", extra={'trace_id': trace_id})
            asyncio.run(start_production_services())
        else:
            logger.info("🔧 Development mode - starting basic services", extra={'trace_id': trace_id})
            
            # Create application
            app = create_bot_application()
            
            # Start background services
            asyncio.create_task(start_background_services())
            
            logger.info("✅ Vanta Bot started successfully", extra={'trace_id': trace_id})
            app.run_polling()
        
    except Exception as e:
        error = handle_exception(e, {"operation": "main"})
        logger.error(f"❌ Failed to start bot: {error.message}")
        sys.exit(1)


if __name__ == "__main__":
    main()