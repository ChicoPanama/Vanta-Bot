"""
Error Middleware
Handles errors consistently across the application
"""

from telegram import Update
from telegram.ext import ContextTypes

from src.utils.errors import handle_exception
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ErrorMiddleware:
    """Middleware for consistent error handling"""

    async def handle_error(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle errors from handlers"""
        error = context.error

        # Log the error
        logger.error(f"Handler error: {error}", exc_info=error)

        # Create a standardized error message
        error_msg = "❌ An error occurred. Please try again or contact support."

        # Try to send error message to user
        try:
            if update and update.effective_message:
                await update.effective_message.reply_text(error_msg)
            elif update and update.callback_query:
                await update.callback_query.answer("❌ Error occurred")
        except Exception as e:
            logger.error(f"Failed to send error message to user: {e}")

        # Report error to external service if configured
        try:
            handled_error = handle_exception(
                error,
                {
                    "update_id": update.update_id if update else None,
                    "user_id": update.effective_user.id
                    if update and update.effective_user
                    else None,
                    "operation": "telegram_handler",
                },
            )

            # Could send to Sentry, monitoring service, etc.
            logger.error(f"Handled error: {handled_error.message}")

        except Exception as e:
            logger.error(f"Failed to handle exception: {e}")
