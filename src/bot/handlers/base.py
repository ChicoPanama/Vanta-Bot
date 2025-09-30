"""Base bot handlers (Phase 5)."""

from telegram import Update
from telegram.ext import Application, CallbackContext, CommandHandler

from src.bot.ui.formatting import h1


def register_base(app: Application, svc_factory):
    """Register base command handlers."""

    async def start(update: Update, context: CallbackContext):
        """Handle /start command."""
        await update.message.reply_markdown(
            h1("Welcome to Vanta-Bot")
            + "\nUse /bind <address> to set your wallet.\nThen /markets, /open, /close, /positions."
        )

    async def help_(update: Update, context: CallbackContext):
        """Handle /help command."""
        await update.message.reply_markdown(
            h1("Help")
            + "\n/bind <addr> - Bind your wallet\n/markets - List markets\n/balance - Check balance\n/positions - View positions\n/open - Open position\n/close - Close position"
        )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_))
