"""Operator commands for signal automation (Phase 6)."""

import json
import logging

import redis
from telegram import Update
from telegram.ext import Application, CallbackContext, CommandHandler

from src.bot.ui.formatting import h1, ok
from src.config.settings import settings

logger = logging.getLogger(__name__)


def _get_queue():
    """Get Redis queue."""
    return redis.from_url(settings.REDIS_URL)


def register_ops(app: Application, svc_factory):
    """Register operator command handlers."""

    async def qpeek(update: Update, context: CallbackContext):
        """Peek at signal queue."""
        try:
            items = _get_queue().lrange(settings.SIGNALS_QUEUE, 0, 9)
            if not items:
                await update.message.reply_markdown("Queue is empty.")
                return

            await update.message.reply_markdown(h1("Queue Top 10"))
            for raw in items:
                decoded = json.loads(raw.decode())
                await update.message.reply_text(str(decoded)[:200])
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

    async def pause_auto(update: Update, context: CallbackContext):
        """Pause automation (requires restart to take effect)."""
        await update.message.reply_markdown(
            ok("Set AUTOMATION_PAUSED=1 in env and restart worker.")
        )

    async def resume_auto(update: Update, context: CallbackContext):
        """Resume automation (requires restart to take effect)."""
        await update.message.reply_markdown(
            ok("Set AUTOMATION_PAUSED=0 in env and restart worker.")
        )

    app.add_handler(CommandHandler("qpeek", qpeek))
    app.add_handler(CommandHandler("pause_auto", pause_auto))
    app.add_handler(CommandHandler("resume_auto", resume_auto))
