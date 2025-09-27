from __future__ import annotations
import re
from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, ConversationHandler, ContextTypes, filters
from src.services.users.user_prefs import prefs_store

ASK_ADDR = 1
ADDR_RX = re.compile(r"^0x[a-fA-F0-9]{40}$")

PROMPT = (
    "🔗 *Link Wallet (optional)*\n"
    "Send your EVM address (read-only). Example:\n"
    "`0x1234...abcd`\n\n"
    "_We do NOT request private keys or signatures._"
)

async def cmd_linkwallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_chat.send_message(PROMPT, parse_mode="Markdown")
    return ASK_ADDR

async def receive_addr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    addr = (update.message.text or "").strip()
    if not ADDR_RX.match(addr):
        await update.effective_chat.send_message("That doesn't look like an EVM address. Try again or /cancel.")
        return ASK_ADDR
    p = prefs_store().get(update.effective_user.id)
    p["linked_wallet"] = addr
    prefs_store().put(update.effective_user.id, p)
    await update.effective_chat.send_message(f"✅ Linked wallet: `{addr}`", parse_mode="Markdown")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_chat.send_message("Cancelled.")
    return ConversationHandler.END

def register(app):
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("linkwallet", cmd_linkwallet)],
        states={ASK_ADDR: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_addr)]},
        fallbacks=[CommandHandler("cancel", cancel)],
        name="linkwallet",
        persistent=False,
    ))
