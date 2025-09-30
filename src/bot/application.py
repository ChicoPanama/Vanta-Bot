"""
Application Factory
Creates and configures the Telegram bot application with proper separation of concerns
"""

from typing import Optional

from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from src.bot.handlers import ai_insights_handlers
from src.bot.handlers.registry import HandlerRegistry
from src.bot.middleware.error_middleware import ErrorMiddleware
from src.bot.middleware.user_middleware import UserMiddleware
from src.config.settings import settings
from src.database.operations import db
from src.services.analytics import InsightsService
from src.utils.errors import handle_exception
from src.utils.logging import get_logger

logger = get_logger(__name__)


class BotApplication:
    """Main application class that handles bot setup and configuration"""

    def __init__(self):
        self.app: Optional[Application] = None
        self.handler_registry = HandlerRegistry()
        self.user_middleware = UserMiddleware()
        self.error_middleware = ErrorMiddleware()

    async def create_application(self) -> Application:
        """Create and configure the Telegram bot application"""
        try:
            # Validate configuration
            settings.validate()
            logger.info("Configuration validated successfully")

            # Create database tables
            await db.create_tables()
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
        try:
            insights_service = InsightsService()
            ai_insights_handlers.set_insights_service(insights_service)
            logger.info("Insights service wired for AI handlers")
        except Exception as e:
            logger.warning(f"Failed to initialise insights service: {e}")

        # Register Phase 2 handlers first (higher priority)
        try:
            from src.bot.handlers.markets_handlers import (
                register as register_markets_handlers,
            )
            from src.bot.handlers.start_handlers import (
                register as register_start_handlers,
            )

            register_start_handlers(self.app)
            register_markets_handlers(self.app)
            logger.info("Phase 2 handlers registered successfully")
        except Exception as e:
            logger.warning(f"Failed to register Phase 2 handlers: {e}")

        # Register Phase 3 handlers (quote & allowance)
        try:
            from src.bot.handlers.quote_handlers import (
                register as register_quote_handlers,
            )

            register_quote_handlers(self.app)
            logger.info("Phase 3 handlers registered successfully")
        except Exception as e:
            logger.warning(f"Failed to register Phase 3 handlers: {e}")

        # Register Phase 4 handlers (positions & exec)
        try:
            from src.bot.handlers.positions_handlers import (
                register as register_positions_handlers,
            )

            register_positions_handlers(self.app)
            logger.info("Phase 4 handlers registered successfully")
        except Exception as e:
            logger.warning(f"Failed to register Phase 4 handlers: {e}")

        # Register Phase 5 handlers (risk education)
        try:
            from src.bot.handlers.risk_handlers import (
                register as register_risk_handlers,
            )

            register_risk_handlers(self.app)
            logger.info("Phase 5 handlers registered successfully")
        except Exception as e:
            logger.warning(f"Failed to register Phase 5 handlers: {e}")

        # Register Phase 6 handlers (admin & health)
        try:
            from src.bot.handlers.admin_handlers import (
                register as register_admin_handlers,
            )

            register_admin_handlers(self.app)
            logger.info("Phase 6 handlers registered successfully")
        except Exception as e:
            logger.warning(f"Failed to register Phase 6 handlers: {e}")

        # Register additional admin commands (/copy, /emergency)
        try:
            from src.bot.handlers.admin_commands import (
                admin_handlers as admin_cmd_handlers,
            )

            # Add only /copy and /emergency to avoid conflicting /status routes
            for h in admin_cmd_handlers:
                try:
                    if getattr(h, "commands", None):
                        cmds = set(h.commands)
                        if "copy" in cmds or "emergency" in cmds:
                            self.app.add_handler(h)
                except Exception:
                    # Fallback: add handler blindly if we can't introspect
                    self.app.add_handler(h)
            logger.info("Additional admin commands registered (/copy, /emergency)")
        except Exception as e:
            logger.warning(f"Failed to register admin_commands: {e}")

        # Register Phase 7 handlers (onboarding & user settings)
        try:
            from src.bot.handlers.mode_handlers import (
                register as register_mode_handlers,
            )
            from src.bot.handlers.onboarding_handlers import (
                register as register_onboarding_handlers,
            )
            from src.bot.handlers.prefs_handlers import (
                register as register_prefs_handlers,
            )
            from src.bot.handlers.wallet_handlers import (
                register as register_wallet_handlers,
            )

            register_onboarding_handlers(self.app)
            register_prefs_handlers(self.app)
            register_wallet_handlers(self.app)
            register_mode_handlers(self.app)
            logger.info("Phase 7 handlers registered successfully")
        except Exception as e:
            logger.warning(f"Failed to register Phase 7 handlers: {e}")

        # Register Phase 8 handlers (copy-trading UX)
        try:
            from src.bot.handlers.alfa_handlers import alfa_handlers
            from src.bot.handlers.copy_handlers import (
                register as register_copy_handlers,
            )
            from src.services.copytrading.copy_service import init as copy_init

            register_copy_handlers(self.app)
            for handler in alfa_handlers:
                self.app.add_handler(handler)
            # Also register copy status/commands (\"/status\", \"/follow\", etc.)
            try:
                from src.bot.handlers.copy_trading_commands import copy_trading_handlers

                for h in copy_trading_handlers:
                    # Avoid re-registering handlers that already exist
                    self.app.add_handler(h)
                logger.info("Copy-trading command handlers registered")
            except Exception as ce:
                logger.warning(f"Failed to register copy_trading_commands: {ce}")
            copy_init()  # Initialize copy-trading database
            logger.info("Phase 8 handlers registered successfully")
        except Exception as e:
            logger.warning(f"Failed to register Phase 8 handlers: {e}")

        # Register existing command handlers
        command_handlers = self.handler_registry.get_command_handlers()
        for command, handler in command_handlers:
            self.app.add_handler(CommandHandler(command, handler))

        # Register conversation handlers
        conversation_handlers = self.handler_registry.get_conversation_handlers()
        for conversation in conversation_handlers:
            self.app.add_handler(conversation)

        # Register callback query handler
        self.app.add_handler(
            CallbackQueryHandler(self.handler_registry.get_callback_handler())
        )

        logger.info("All handlers registered successfully")


async def create_bot_application() -> Application:
    """Factory function to create configured bot application"""
    bot_app = BotApplication()
    return await bot_app.create_application()
