"""
User Middleware
Handles user validation and common user operations
"""

from functools import wraps
from typing import Callable

from telegram import Update
from telegram.ext import ContextTypes

from src.database.operations import db
from src.utils.logging import get_logger

logger = get_logger(__name__)


class UserMiddleware:
    """Middleware for user validation and common operations"""

    @staticmethod
    def require_user(func: Callable) -> Callable:
        """Decorator to ensure user exists in database before handler execution"""

        @wraps(func)
        async def wrapper(
            update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
        ):
            user_id = update.effective_user.id

            # Get user from database
            db_user = await db.get_user(user_id)
            if not db_user:
                error_msg = "❌ User not found. Please /start first."

                if update.callback_query:
                    await update.callback_query.answer(error_msg)
                else:
                    await update.message.reply_text(error_msg)
                return

            # Add user to context for easy access
            context.user_data["db_user"] = db_user

            return await func(update, context, *args, **kwargs)

        return wrapper

    @staticmethod
    def get_user_from_context(context: ContextTypes.DEFAULT_TYPE):
        """Get database user from context"""
        return context.user_data.get("db_user")

    @staticmethod
    def validate_user_interface_type(context: ContextTypes.DEFAULT_TYPE) -> str:
        """Get and validate user interface type"""
        return context.user_data.get("user_type", "simple")
