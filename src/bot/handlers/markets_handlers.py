from __future__ import annotations
from decimal import Decimal
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

from src.services.markets.markets_provider import list_pairs, get_last_price
from src.bot.ui.keyboards import kb, chunk_buttons
from src.bot.ui.formatting import fmt_px, fmt_usd
from src.services.trading.trade_drafts import draft_store, TradeDraft
from src.services.users.user_prefs import prefs_store


PAGE_SIZE = 6
LEV_CHIPS = [5, 10, 25, 50, 100]
COLL_CHIPS = [25, 100, 250, 500, 1000]


def _page_kb(pairs, page, total_pages, default_pair=None) -> InlineKeyboardMarkup:
    pair_buttons = []
    for p in pairs:
        if p == default_pair:
            pair_buttons.append(InlineKeyboardButton(f"⭐ {p}", callback_data=f"pair:{p}"))
        else:
            pair_buttons.append(InlineKeyboardButton(p, callback_data=f"pair:{p}"))
    rows = chunk_buttons(pair_buttons, n=2)

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"mk:pg:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"mk:pg:{page + 1}"))
    if nav:
        rows.append(nav)

    return InlineKeyboardMarkup(rows)


async def cmd_markets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pairs, total = await list_pairs(page=0, page_size=PAGE_SIZE)
    
    # Get user's default pair preference
    uid = update.effective_user.id
    p = prefs_store().get(uid)
    default_pair = p.get("default_pair")
    
    # Add default pair shortcut if it exists and is available
    if default_pair and default_pair in pairs:
        pairs.remove(default_pair)
        pairs.insert(0, default_pair)
    
    await update.effective_chat.send_message(
        "Select a market:", reply_markup=_page_kb(pairs, 0, total, default_pair)
    )


async def cb_markets_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, _, page = q.data.split(":")
    page = int(page)
    pairs, total = await list_pairs(page=page, page_size=PAGE_SIZE)
    
    # Get user's default pair preference
    uid = q.from_user.id
    p = prefs_store().get(uid)
    default_pair = p.get("default_pair")
    
    # Add default pair shortcut if it exists and is available (only on first page)
    if page == 0 and default_pair and default_pair in pairs:
        pairs.remove(default_pair)
        pairs.insert(0, default_pair)
    
    await q.edit_message_text(
        "Select a market:", reply_markup=_page_kb(pairs, page, total, default_pair if page == 0 else None)
    )


async def cb_select_pair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, pair = q.data.split(":", 1)
    price = await get_last_price(pair)

    # Get user preferences for chips
    uid = q.from_user.id
    p = prefs_store().get(uid)
    user_lev_chips = p.get("lev_presets", LEV_CHIPS)
    user_coll_chips = p.get("collateral_presets", COLL_CHIPS)

    text = (
        f"*{pair}*\n"
        f"Price: {fmt_px(price)}\n\n"
        f"Quick Trade:\n"
        f"1) Choose side   2) Leverage   3) Collateral"
    )

    # side row
    side_row = [("Long 🟢", f"qt:side:{pair}:LONG"), ("Short 🔴", f"qt:side:{pair}:SHORT")]

    # leverage row - use user preferences
    lev_btns = [(f"{x}×", f"qt:lev:{pair}:{x}") for x in user_lev_chips]
    lev_row = chunk_buttons(
        [InlineKeyboardButton(t, callback_data=c) for (t, c) in lev_btns], n=5
    )[0]

    # collateral rows - use user preferences
    coll_btns = [(f"${c}", f"qt:coll:{pair}:{c}") for c in user_coll_chips]
    coll_rows = chunk_buttons(
        [InlineKeyboardButton(t, callback_data=c) for (t, c) in coll_btns], n=5
    )

    rows = [
        [InlineKeyboardButton(t, callback_data=c) for (t, c) in side_row],
        lev_row,
        *coll_rows,
        [InlineKeyboardButton("🔄 Refresh", callback_data=f"pair:{pair}")],
        [InlineKeyboardButton("⬅️ Markets", callback_data="nav:markets")],
    ]

    await q.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(rows))


async def cb_nav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, dest = q.data.split(":", 1)

    if dest == "markets":
        pairs, total = await list_pairs(page=0, page_size=PAGE_SIZE)
        
        # Get user's default pair preference
        uid = q.from_user.id
        p = prefs_store().get(uid)
        default_pair = p.get("default_pair")
        
        # Add default pair shortcut if it exists and is available
        if default_pair and default_pair in pairs:
            pairs.remove(default_pair)
            pairs.insert(0, default_pair)
        
        await q.edit_message_text("Select a market:", reply_markup=_page_kb(pairs, 0, total, default_pair))
    elif dest == "quick":
        await q.edit_message_text("Pick a market via /markets, then use the Quick Trade buttons.")
    elif dest == "positions":
        # Phase 4 will implement a full positions view; placeholder for now:
        await q.edit_message_text("Your positions will appear here (Phase 4). Use /positions if available.")


async def cb_qt_side(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, _, pair, side = q.data.split(":")
    d = draft_store.get(q.from_user.id) or TradeDraft(user_id=q.from_user.id, pair=pair)
    d.pair, d.side = pair, side
    draft_store.put(d)
    await q.answer(text=f"Side set to {side}")


async def cb_qt_lev(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, _, pair, lev = q.data.split(":")
    d = draft_store.get(q.from_user.id) or TradeDraft(user_id=q.from_user.id, pair=pair)
    d.pair, d.leverage = pair, Decimal(lev)
    draft_store.put(d)
    await q.answer(text=f"Leverage set to {lev}×")


async def cb_qt_coll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, _, pair, coll = q.data.split(":")
    d = draft_store.get(q.from_user.id) or TradeDraft(user_id=q.from_user.id, pair=pair)
    d.pair, d.collateral_usdc = pair, Decimal(coll)
    draft_store.put(d)
    await show_draft_card(update, context, pair)


async def show_draft_card(update: Update, context: ContextTypes.DEFAULT_TYPE, pair: str):
    q = update.callback_query
    d = draft_store.get(q.from_user.id)

    side = d.side or "—"
    lev = f"{d.leverage}×" if d.leverage else "—"
    col = fmt_usd(d.collateral_usdc) if d.collateral_usdc else "—"

    text = (
        f"*Draft Trade* — {pair}\n"
        f"Side: {side}\n"
        f"Leverage: {lev}\n"
        f"Collateral: {col}\n\n"
        f"Next (Phase 3): Show live quote (fees, loss protection, spread/impact) before execution."
    )

    rows = [
        [("📊 Show Quote (Phase 3)", f"qt:quote:{pair}")],
        [("♻️ Reset Draft", f"qt:reset:{pair}")],
        [("⬅️ Back to Pair", f"pair:{pair}")],
    ]
    await q.edit_message_text(text, parse_mode="Markdown", reply_markup=kb(rows))


async def cb_qt_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, _, pair = q.data.split(":")
    draft_store.clear(q.from_user.id)
    await q.edit_message_text("Draft cleared.", reply_markup=kb([[("⬅️ Back to Pair", f"pair:{pair}")]]))


def register(app):
    app.add_handler(CommandHandler("markets", cmd_markets))
    app.add_handler(CallbackQueryHandler(cb_markets_pagination, pattern=r"^mk:pg:\d+$"))
    app.add_handler(CallbackQueryHandler(cb_select_pair, pattern=r"^pair:.+"))
    app.add_handler(CallbackQueryHandler(cb_nav, pattern=r"^nav:.+"))
    app.add_handler(CallbackQueryHandler(cb_qt_side, pattern=r"^qt:side:.+"))
    app.add_handler(CallbackQueryHandler(cb_qt_lev, pattern=r"^qt:lev:.+"))
    app.add_handler(CallbackQueryHandler(cb_qt_coll, pattern=r"^qt:coll:.+"))
    app.add_handler(CallbackQueryHandler(cb_qt_reset, pattern=r"^qt:reset:.+"))
    # NOTE: qt:quote will be implemented in Phase 3
