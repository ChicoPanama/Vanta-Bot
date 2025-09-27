from __future__ import annotations
from decimal import Decimal
from telegram import Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from src.services.trading.execution_service import get_execution_service
# from src.config.settings import settings
from src.config.settings_new import settings
from src.bot.ui.keyboards import kb
from src.bot.ui.formatting import fmt_usd, fmt_px
from src.utils.ratelimit import pos_limiter

# Import for mode badge
try:
  from src.config.flags_standalone import is_live
except ImportError:
  def is_live():
    import os
    return os.getenv("COPY_EXECUTION_MODE", "DRY").upper() == "LIVE"


def _positions_text(positions):
    if not positions:
        return "You have no open positions."
    
    # Add mode badge
    mode_badge = "(LIVE)" if is_live() else "(DRY)"
    lines = [f"*Your Open Positions* {mode_badge}"]
    for p in positions:
        pair = p.get("pair", "—")
        side = p.get("side", "—")
        lev  = p.get("leverage") or "—"
        notional = p.get("notional_usd")
        pnl = p.get("pnl_usd")
        entry = p.get("entry_px")

        row = f"• {pair} {side}  lev:{lev}  size:{fmt_usd(notional) if notional else '—'}"
        if pnl is not None:
            try:
                row += f"  pnl:{fmt_usd(Decimal(pnl))}"
            except Exception:
                row += f"  pnl:{pnl}"
        if entry is not None:
            row += f"  entry:{entry}"
        lines.append(row)
    return "\n".join(lines)


def _close_rows(positions):
    rows = []
    for p in positions:
        idx = p.get("index")
        if idx is None:
            continue
        rows.append([
            ("Close 25%", f"pos:close:{idx}:0.25"),
            ("Close 50%", f"pos:close:{idx}:0.50"),
            ("Close 100%", f"pos:close:{idx}:1.0"),
        ])
    return rows


async def cmd_positions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not pos_limiter.allow(update.effective_user.id):
        await update.effective_chat.send_message("Slow down a sec…")
        return
    
    svc = get_execution_service(settings)
    positions = await svc.get_positions()
    text = _positions_text(positions)

    rows = []
    if positions:
        rows += _close_rows(positions)
    rows.append([("🔄 Refresh", "pos:refresh")])

    await update.effective_chat.send_message(text, parse_mode="Markdown", reply_markup=kb(rows))


async def cb_positions_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    if not pos_limiter.allow(q.from_user.id):
        await q.answer("Slow down a sec…", show_alert=False)
        return
    
    svc = get_execution_service(settings)
    positions = await svc.get_positions()
    text = _positions_text(positions)
    rows = []
    if positions:
        rows += _close_rows(positions)
    rows.append([("🔄 Refresh", "pos:refresh")])
    await q.edit_message_text(text, parse_mode="Markdown", reply_markup=kb(rows))


async def cb_positions_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, _, idx, frac = q.data.split(":")
    svc = get_execution_service(settings)
    ok, msg, res = await svc.execute_close(position_index=int(idx), fraction=Decimal(frac))
    txh = res.get("tx_hash") if isinstance(res, dict) else None

    prefix = "✅" if ok else "❌"
    txt = f"{prefix} {msg}"
    if ok and txh:
        txt += f"\n\n*tx:* `{txh}`"
        # Add BaseScan link for Base mainnet
        txt += f"\n[View on BaseScan](https://basescan.org/tx/{txh})"
    rows = [[("📂 Back to Positions", "pos:refresh")]]
    await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=kb(rows))


def register(app):
    app.add_handler(CommandHandler("positions", cmd_positions))
    app.add_handler(CallbackQueryHandler(cb_positions_refresh, pattern=r"^pos:refresh$"))
    app.add_handler(CallbackQueryHandler(cb_positions_close, pattern=r"^pos:close:\d+:\d+(\.\d+)?$"))
