from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from src.services.users.user_prefs import prefs_store

WELCOME = (
    "👋 *Welcome to Vanta-Bot*\n\n"
    "You're a tap away from trading on Avantis:\n"
    "1) /markets → Pick a pair\n"
    "2) Choose ↕️ *Long/Short*, ⚙️ *Leverage*, 💵 *Collateral*\n"
    "3) 📊 *Quote* → see fees, slippage, allowance\n"
    "4) ✅ Approve USDC (once), then 🚀 Execute\n\n"
    "📚 Try /analyze for educational risk insights.\n"
    "⚙️ Configure defaults in /prefs. Link wallet (view-only) via /linkwallet.\n"
    "_All trades honor your server mode. Client /mode is a UI preference only._"
)

HELP = (
    "*Quick Commands*\n"
    "• /markets — Browse pairs\n"
    "• /positions — View & close (25/50/100%)\n"
    "• /prefs — Default slippage, leverage & collateral chips, favorites\n"
    "• /mode — Choose DRY/LIVE *preference* (server controls real mode)\n"
    "• /analyze — Risk analysis (educational only)\n"
    "• /calc — Position size helper\n"
    "• /health — Uptime & circuit status\n"
    "• /diag — Diagnostics\n"
)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ = prefs_store().get(update.effective_user.id)  # creates defaults lazily
    await update.effective_chat.send_message(WELCOME, parse_mode="Markdown")
    await update.effective_chat.send_message(
        "Try */markets* to begin.", parse_mode="Markdown"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_chat.send_message(HELP, parse_mode="Markdown")


def register(app):
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
