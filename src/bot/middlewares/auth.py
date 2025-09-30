"""User context middleware (Phase 5)."""

import logging
from types import SimpleNamespace

from telegram import Update
from telegram.ext import BaseHandler, CallbackContext

logger = logging.getLogger(__name__)


async def user_context_middleware(update: Update, context: CallbackContext):
    """Add user context to callback context.

    Args:
        update: Telegram update
        context: Callback context
    """
    user = update.effective_user
    context.user = SimpleNamespace(tg_id=user.id if user else None)
    logger.debug(f"User context: tg_id={context.user.tg_id}")
