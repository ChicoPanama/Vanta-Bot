from __future__ import annotations
from decimal import Decimal
from telegram import Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from src.services.users.user_prefs import prefs_store
from src.bot.ui.keyboards import kb
from src.utils.logging import get_logger

logger = get_logger(__name__)

def _prefs_text(p):
    fav = ", ".join(p.get("ui_favorites", []))
    lev = ", ".join([str(x) for x in p.get("lev_presets", [])])
    col = ", ".join([str(x) for x in p.get("collateral_presets", [])])
    return (
        "*Preferences*\n"
        f"• Default pair: {p.get('default_pair')}\n"
        f"• Favorites: {fav}\n"
        f"• Default slippage: {p.get('default_slippage_pct')}%\n"
        f"• Leverage chips: {lev}\n"
        f"• Collateral chips (USDC): {col}\n"
        f"• Mode preference: {p.get('preferred_mode')}\n"
        f"• Linked wallet: {p.get('linked_wallet') or '—'}\n"
        "\nTap buttons to adjust. All optional."
    )

async def cmd_prefs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    p = prefs_store().get(uid)
    rows = [
        [("Slippage 0.5%", "pf:slip:0.5"), ("1%", "pf:slip:1"), ("2%", "pf:slip:2")],
        [("Leverage chips 5/10/25/50", "pf:lev:5,10,25,50"), ("10/25/50/100", "pf:lev:10,25,50,100")],
        [("Collateral 50/100/250/500", "pf:col:50,100,250,500"), ("100/250/500/1000", "pf:col:100,250,500,1000")],
        [("Favorites ETH,BTC", "pf:fav:ETH/USD,BTC/USD"), ("+SOL", "pf:fav:ETH/USD,BTC/USD,SOL/USD")],
        [("Default pair ETH/USD", "pf:pair:ETH/USD"), ("BTC/USD", "pf:pair:BTC/USD")],
        [("Mode pref DRY", "pf:mode:DRY"), ("LIVE (UI only)", "pf:mode:LIVE")],
    ]
    await update.effective_chat.send_message(_prefs_text(p), parse_mode="Markdown", reply_markup=kb(rows))

async def cb_prefs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    p = prefs_store().get(uid)

    parts = q.data.split(":")
    _, kind, value = parts[0], parts[1], ":".join(parts[2:])

    if kind == "slip":
        try:
            p["default_slippage_pct"] = float(value)
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid slippage value '{value}': {e}")
            pass
    elif kind == "lev":
        try:
            p["lev_presets"] = [int(x) for x in value.split(",")]
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid leverage presets '{value}': {e}")
            pass
    elif kind == "col":
        try:
            p["collateral_presets"] = [int(x) for x in value.split(",")]
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid collateral presets '{value}': {e}")
            pass
    elif kind == "fav":
        p["ui_favorites"] = value.split(",")
    elif kind == "pair":
        p["default_pair"] = value
    elif kind == "mode":
        # UI preference only; server live mode still enforced in execution
        p["preferred_mode"] = value

    prefs_store().put(uid, p)

    # Re-render
    rows = [
        [("Slippage 0.5%", "pf:slip:0.5"), ("1%", "pf:slip:1"), ("2%", "pf:slip:2")],
        [("Leverage chips 5/10/25/50", "pf:lev:5,10,25,50"), ("10/25/50/100", "pf:lev:10,25,50,100")],
        [("Collateral 50/100/250/500", "pf:col:50,100,250,500"), ("100/250/500/1000", "pf:col:100,250,500,1000")],
        [("Favorites ETH,BTC", "pf:fav:ETH/USD,BTC/USD"), ("+SOL", "pf:fav:ETH/USD,BTC/USD,SOL/USD")],
        [("Default pair ETH/USD", "pf:pair:ETH/USD"), ("BTC/USD", "pf:pair:BTC/USD")],
        [("Mode pref DRY", "pf:mode:DRY"), ("LIVE (UI only)", "pf:mode:LIVE")],
    ]
    await q.edit_message_text(_prefs_text(p), parse_mode="Markdown", reply_markup=kb(rows))

def register(app):
    app.add_handler(CommandHandler("prefs", cmd_prefs))
    app.add_handler(CallbackQueryHandler(cb_prefs, pattern=r"^pf:"))
