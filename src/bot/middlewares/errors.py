"""Global error handler (Phase 5)."""

import logging

from telegram import Update
from telegram.ext import CallbackContext

from src.bot.ui.formatting import warn

logger = logging.getLogger(__name__)


async def error_handler(update: Update, context: CallbackContext):
    """Handle errors globally.

    Args:
        update: Telegram update
        context: Callback context with error
    """
    msg = str(context.error) if context.error else "Unexpected error."
    logger.error(f"Bot error: {msg}", exc_info=context.error)

    try:
        if update and update.effective_chat:
            await update.effective_chat.send_message(warn(msg), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Failed to send error message: {e}")
