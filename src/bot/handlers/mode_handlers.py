from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from src.config.flags_standalone import is_live  # server-side truth
from src.services.users.user_prefs import prefs_store

EXPL = (
    "*Mode Preference*\n"
    "• Your personal preference helps us tailor the UI.\n"
    "• Actual execution mode is controlled by the server and shown on the Quote/Execute screens.\n"
)


async def cmd_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    uid = update.effective_user.id
    p = prefs_store().get(uid)
    if not args:
        await update.effective_chat.send_message(
            f"{EXPL}\nCurrent preference: *{p.get('preferred_mode')}*\nServer mode (truth): *{'LIVE' if is_live() else 'DRY'}*",
            parse_mode="Markdown",
        )
        return
    choice = args[0].upper()
    if choice not in ("DRY", "LIVE"):
        await update.effective_chat.send_message(
            "Usage: /mode DRY  or  /mode LIVE (UI preference only)"
        )
        return
    p["preferred_mode"] = choice
    prefs_store().put(uid, p)
    await update.effective_chat.send_message(
        f"✅ Preference saved: *{choice}*. Server mode is *{'LIVE' if is_live() else 'DRY'}*.",
        parse_mode="Markdown",
    )


def register(app):
    app.add_handler(CommandHandler("mode", cmd_mode))
