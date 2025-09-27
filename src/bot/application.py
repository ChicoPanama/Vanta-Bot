"""
Application Factory
Creates and configures the Telegram bot application with proper separation of concerns
"""

from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
from typing import List, Tuple

from src.config.settings import settings
from src.utils.logging import get_logger
from src.utils.errors import handle_exception
from src.database.operations import db
from src.bot.handlers.registry import HandlerRegistry
from src.bot.middleware.user_middleware import UserMiddleware
from src.bot.middleware.error_middleware import ErrorMiddleware

logger = get_logger(__name__)


class BotApplication:
    """Main application class that handles bot setup and configuration"""
    
    def __init__(self):
        self.app: Application = None
        self.handler_registry = HandlerRegistry()
        self.user_middleware = UserMiddleware()
        self.error_middleware = ErrorMiddleware()
    
    def create_application(self) -> Application:
        """Create and configure the Telegram bot application"""
        try:
            # Validate configuration
            settings.validate()
            logger.info("Configuration validated successfully")
            
            # Create database tables
            db.create_tables()
            logger.info("Database tables created/verified")
            
            # Create application
            self.app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
            logger.info("Telegram application created")
            
            # Register middleware
            self._register_middleware()
            
            # Register handlers
            self._register_handlers()
            
            return self.app
            
        except Exception as e:
            error = handle_exception(e, {"operation": "create_application"})
            logger.error(f"Failed to create application: {error.message}")
            raise
    
    def _register_middleware(self):
        """Register application middleware"""
        # Add middleware for user validation and error handling
        self.app.add_error_handler(self.error_middleware.handle_error)
        logger.info("Middleware registered")
    
    def _register_handlers(self):
        """Register all command and callback handlers"""
        # Register command handlers
        command_handlers = self.handler_registry.get_command_handlers()
        for command, handler in command_handlers:
            self.app.add_handler(CommandHandler(command, handler))
        
        # Register conversation handlers
        conversation_handlers = self.handler_registry.get_conversation_handlers()
        for conversation in conversation_handlers:
            self.app.add_handler(conversation)
        
        # Register callback query handler
        self.app.add_handler(CallbackQueryHandler(
            self.handler_registry.get_callback_handler()
        ))
        
        logger.info("All handlers registered successfully")


def create_bot_application() -> Application:
    """Factory function to create configured bot application"""
    bot_app = BotApplication()
    return bot_app.create_application()
