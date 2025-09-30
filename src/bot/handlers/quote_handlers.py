from __future__ import annotations

from decimal import Decimal

from telegram import Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from src.bot.ui.formatting import fmt_usd
from src.bot.ui.keyboards import kb
from src.config.settings import settings  # unified central settings
from src.services.trading.execution_service import SLIPPAGE_STEPS, get_execution_service
from src.services.trading.trade_drafts import draft_store
from src.services.users.user_prefs import prefs_store
from src.utils.ratelimit import quote_limiter

# Import for mode badge
try:
    from src.config.flags_standalone import is_live
except ImportError:

    def is_live():
        import os

        return os.getenv("COPY_EXECUTION_MODE", "DRY").upper() == "LIVE"


def _slippage_row(pair: str, current: Decimal):
    row = []
    for s in SLIPPAGE_STEPS:
        txt = f"{s}%"
        if s == current:
            txt = f"✅ {txt}"
        row.append((txt, f"qt:slip:{pair}:{s}"))
    return [row]


def _quote_card_text(qd):
    # qd is the `data` dict from QuoteResult
    pair = qd.get("pair")
    side = qd.get("side")
    lev = qd.get("leverage")
    col = qd.get("collateral_usdc")

    # Add mode badge
    mode_badge = "(LIVE)" if is_live() else "(DRY)"
    notional = qd.get("notional_usd")
    fee = qd.get("fee_usdc")
    prot = qd.get("loss_protection")
    spread = qd.get("pair_spread_bps")
    impact = qd.get("impact_spread_bps")
    slip = qd.get("slippage_pct")
    allow = qd.get("allowance")
    usdc_req = qd.get("usdc_required")

    prot_str = "—"
    if isinstance(prot, dict):
        # render key fields if present
        lp = prot.get("protection") or prot.get("value") or prot
        prot_str = str(lp)

    return (
        f"*Quote — {pair}* {mode_badge}\n"
        f"Side: {side} | Leverage: {lev}×\n"
        f"Collateral: {fmt_usd(Decimal(col)) if col else '—'}\n"
        f"Notional: {fmt_usd(Decimal(notional)) if notional else '—'}\n\n"
        f"Fees: {fmt_usd(Decimal(fee)) if fee else '—'}\n"
        f"Loss protection: {prot_str}\n"
        f"Pair spread: {spread if spread is not None else '—'} bps\n"
        f"Impact spread: {impact if impact is not None else '—'} bps\n"
        f"Slippage: {slip}%\n\n"
        f"Allowance: {fmt_usd(Decimal(allow)) if allow else '—'} "
        f"| Required: {fmt_usd(Decimal(usdc_req)) if usdc_req else '—'}"
    )


async def cb_show_quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if not quote_limiter.allow(q.from_user.id):
        await q.answer("Slow down a sec…", show_alert=False)
        return

    _, _, pair = q.data.split(":")
    d = draft_store.get(q.from_user.id)

    # Apply user's default slippage preference if not already set
    uid = q.from_user.id
    p = prefs_store().get(uid)
    user_slip = p.get("default_slippage_pct", 1.0)
    if "slippage_pct" not in context.user_data:
        context.user_data["slippage_pct"] = Decimal(str(user_slip))

    svc = get_execution_service(settings)
    res = await svc.quote_from_draft(draft=d)

    if not res.ok:
        await q.edit_message_text(
            f"❌ {res.message}\n\nPlease select side, leverage and collateral on the Pair screen.",
            reply_markup=kb([[("⬅️ Back to Pair", f"pair:{pair}")]]),
        )
        return

    qd = res.data or {}
    txt = _quote_card_text(qd)

    needs_approval = bool(qd.get("needs_approval"))
    slip = Decimal(
        str(
            qd.get("slippage_pct")
            or context.user_data.get("slippage_pct")
            or settings.default_slippage_pct
        )
    )

    rows = []
    # slippage selection row
    rows += _slippage_row(pair, slip)

    # derive size_usd and lev for the inline analyzer (educational)
    size_usd = qd.get("collateral_usdc") or "0"
    lev_str = qd.get("leverage") or "1"
    rows += [[("📚 View Risk", f"qt:viewrisk:{qd.get('pair')}:{size_usd}:{lev_str}")]]

    # actions
    if needs_approval:
        rows.append([("✅ Approve USDC", f"qt:approve:{pair}")])

    rows.append([("🚀 Proceed to Execute (Phase 4)", f"qt:exec:{pair}")])
    rows.append([("⬅️ Back to Pair", f"pair:{pair}")])

    await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=kb(rows))


async def cb_set_slippage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if not quote_limiter.allow(q.from_user.id):
        await q.answer("Slow down a sec…", show_alert=False)
        return

    _, _, pair, slip = q.data.split(":")
    d = draft_store.get(q.from_user.id)
    if not d:
        await q.edit_message_text(
            "No draft found. Go back to /markets.",
            reply_markup=kb([[("⬅️ Markets", "nav:markets")]]),
        )
        return

    # Requote with chosen slippage (store in context.user_data for Phase 4 usage)
    context.user_data["slippage_pct"] = Decimal(slip)

    svc = get_execution_service(settings)
    res = await svc.quote_from_draft(draft=d, slippage_pct=Decimal(slip))
    if not res.ok:
        await q.edit_message_text(
            f"❌ {res.message}",
            reply_markup=kb([[("⬅️ Back to Pair", f"pair:{d.pair}")]]),
        )
        return

    qd = res.data or {}
    txt = _quote_card_text(qd)

    rows = []
    rows += _slippage_row(pair, Decimal(slip))

    # derive size_usd and lev for the inline analyzer (educational)
    size_usd = qd.get("collateral_usdc") or "0"
    lev_str = qd.get("leverage") or "1"
    rows += [[("📚 View Risk", f"qt:viewrisk:{qd.get('pair')}:{size_usd}:{lev_str}")]]

    if bool(qd.get("needs_approval")):
        rows.append([("✅ Approve USDC", f"qt:approve:{pair}")])
    rows.append([("🚀 Proceed to Execute (Phase 4)", f"qt:exec:{pair}")])
    rows.append([("⬅️ Back to Pair", f"pair:{pair}")])

    await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=kb(rows))


async def cb_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, _, pair = q.data.split(":")

    d = draft_store.get(q.from_user.id)
    if not d:
        await q.edit_message_text(
            "No draft found.", reply_markup=kb([[("⬅️ Markets", "nav:markets")]])
        )
        return

    svc = get_execution_service(settings)

    # Recompute quote to ensure we have up-to-date usdc_required
    res = await svc.quote_from_draft(draft=d)
    if not res.ok or not res.data:
        await q.edit_message_text(
            f"❌ {res.message}", reply_markup=kb([[("⬅️ Back to Pair", f"pair:{pair}")]])
        )
        return

    usdc_required = Decimal(str(res.data.get("usdc_required") or "0"))
    ok, msg = await svc.approve_if_needed(usdc_required)

    # Re-draw quote after approve attempt
    res2 = await svc.quote_from_draft(draft=d)
    if not res2.ok:
        await q.edit_message_text(
            f"{'✅' if ok else '❌'} {msg}\n\n{res2.message}",
            reply_markup=kb([[("⬅️ Back to Pair", f"pair:{pair}")]]),
        )
        return

    qd = res2.data or {}
    txt = _quote_card_text(qd)
    needs_approval = bool(qd.get("needs_approval"))
    slip = Decimal(
        str(
            qd.get("slippage_pct")
            or context.user_data.get("slippage_pct")
            or settings.default_slippage_pct
        )
    )

    rows = []
    rows += _slippage_row(pair, slip)
    if needs_approval:
        rows.append([("✅ Approve USDC", f"qt:approve:{pair}")])
    rows.append([("🚀 Proceed to Execute (Phase 4)", f"qt:exec:{pair}")])
    rows.append([("⬅️ Back to Pair", f"pair:{pair}")])

    prefix = "✅ " if ok else "❌ "
    await q.edit_message_text(
        prefix + msg + "\n\n" + txt, parse_mode="Markdown", reply_markup=kb(rows)
    )


def _result_card(ok, msg, tx_hash=None, pair=None, side=None):
    prefix = "✅" if ok else "❌"
    base = f"{prefix} {msg}"
    if ok and tx_hash:
        base += f"\n\n*tx:* `{tx_hash}`"
        # Add BaseScan link for Base mainnet
        base += f"\n[View on BaseScan](https://basescan.org/tx/{tx_hash})"
    if pair and side:
        base += f"\n*trade:* {pair} {side}"
    return base


async def cb_exec_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, _, pair = q.data.split(":")

    d = draft_store.get(q.from_user.id)
    if not d or d.pair != pair:
        await q.edit_message_text(
            "No draft found; go back to /markets.",
            reply_markup=kb([[("⬅️ Markets", "nav:markets")]]),
        )
        return

    # slippage from user context if set
    slip = context.user_data.get("slippage_pct")
    svc = get_execution_service(settings)

    ok, msg, res = await svc.execute_open(draft=d, slippage_pct=slip)

    txh = res.get("tx_hash") if isinstance(res, dict) else None
    txt = _result_card(ok, msg, txh, pair=pair, side=d.side)
    rows = [
        [("📂 View Positions", "nav:positions")],
        [("📊 Re-Quote", f"qt:quote:{pair}")],
        [("⬅️ Back to Pair", f"pair:{pair}")],
    ]
    await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=kb(rows))


# Debug command for manual quoting:
async def cmd_a_quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Usage: /a_quote <PAIR> <SIDE> <COLL_USDC> <LEV> [slip%]
    Example: /a_quote ETH/USD LONG 100 25 1
    """
    args = context.args or []
    if len(args) < 4:
        await update.effective_chat.send_message(
            "Usage: `/a_quote <PAIR> <SIDE> <COLL_USDC> <LEV> [slip%]`",
            parse_mode="Markdown",
        )
        return

    pair, side, coll, lev = args[:4]
    slip = (
        Decimal(args[4])
        if len(args) > 4
        else Decimal(str(settings.default_slippage_pct or 1))
    )

    # Build a temporary draft
    draft = draft_store.get(update.effective_user.id)
    if not draft or draft.pair != pair:
        from src.services.trading.trade_drafts import TradeDraft

        draft = TradeDraft(
            user_id=update.effective_user.id,
            pair=pair,
            side=side.upper(),
            collateral_usdc=Decimal(coll),
            leverage=Decimal(lev),
        )
        draft_store.put(draft)
    else:
        draft.side = side.upper()
        draft.collateral_usdc = Decimal(coll)
        draft.leverage = Decimal(lev)
        draft_store.put(draft)

    svc = get_execution_service(settings)
    res = await svc.quote_from_draft(draft, slip)
    if not res.ok or not res.data:
        await update.effective_chat.send_message(f"❌ {res.message}")
        return

    txt = _quote_card_text(res.data)
    await update.effective_chat.send_message(txt, parse_mode="Markdown")


def register(app):
    app.add_handler(CallbackQueryHandler(cb_show_quote, pattern=r"^qt:quote:.+"))
    app.add_handler(CallbackQueryHandler(cb_set_slippage, pattern=r"^qt:slip:.+"))
    app.add_handler(CallbackQueryHandler(cb_approve, pattern=r"^qt:approve:.+"))
    app.add_handler(
        CallbackQueryHandler(cb_exec_trade, pattern=r"^qt:exec:.+")
    )  # ← now executes
    app.add_handler(CommandHandler("a_quote", cmd_a_quote))
