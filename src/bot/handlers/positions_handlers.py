"""Position viewing handlers (Phase 5)."""

from telegram import Update
from telegram.ext import Application, CallbackContext, CommandHandler

from src.bot.ui.formatting import code, h1, usdc1e6, warn
from src.repositories.user_wallets_repo import get_wallet


def register_positions(app: Application, svc_factory):
    """Register position command handlers."""

    async def positions(update: Update, context: CallbackContext):
        """Handle /positions command."""
        w3, db, svc = svc_factory()
        try:
            addr = get_wallet(db, context.user.tg_id)
            if not addr:
                await update.message.reply_markdown(
                    warn("No wallet bound. Use /bind <address>.")
                )
                return

            rows = svc.list_user_positions(addr)
            if not rows:
                await update.message.reply_markdown(h1("Positions") + "\nNone.")
            else:
                lines = [h1("Positions")]
                for r in rows:
                    side = "LONG" if r["is_long"] else "SHORT"
                    size = usdc1e6(r["size_usd_1e6"])
                    coll = usdc1e6(r["collateral_1e6"])
                    lines.append(
                        f"{code(r['symbol'])} • {side} • Size: {size} • Coll: {coll}"
                    )

                await update.message.reply_markdown("\n".join(lines))
        finally:
            db.close()

    app.add_handler(CommandHandler("positions", positions))
