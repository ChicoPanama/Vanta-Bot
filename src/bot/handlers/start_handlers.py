from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from src.bot.ui.keyboards import kb

START_KB = kb(
    [
        [("📈 Browse Markets", "nav:markets")],
        [("⚡ Quick Trade", "nav:quick")],
        [("📂 My Positions", "nav:positions")],
    ]
)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_chat.send_message(
        "Welcome to Vanta-Bot — Avantis trading on Telegram.\n\nChoose an option:",
        reply_markup=START_KB,
    )


def register(app):
    app.add_handler(CommandHandler("start", cmd_start))
