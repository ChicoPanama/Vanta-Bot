"""Market information handlers (Phase 5)."""

from telegram import Update
from telegram.ext import Application, CallbackContext, CommandHandler

from src.bot.ui.formatting import code, h1, usdc1e6


def register_markets(app: Application, svc_factory):
    """Register market command handlers."""

    async def markets(update: Update, context: CallbackContext):
        """Handle /markets command."""
        w3, db, svc = svc_factory()
        try:
            views = svc.list_markets()
            lines = [h1("Markets")]

            for sym, v in views.items():
                if v.price is not None:
                    price = f"{(v.price / (10**v.price_decimals)):.2f}"
                else:
                    price = "—"

                src = v.source or "—"
                min_pos = usdc1e6(v.min_position_usd_1e6)

                lines.append(
                    f"{code(sym)} • Price: {price} • Min: {min_pos} • Feed: {src}"
                )

            await update.message.reply_markdown("\n".join(lines))
        finally:
            db.close()

    app.add_handler(CommandHandler("markets", markets))
