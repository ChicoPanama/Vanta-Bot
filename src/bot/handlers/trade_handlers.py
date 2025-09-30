"""Trade execution handlers with guided flows (Phase 5)."""

import logging

from telegram import Update
from telegram.ext import (
    Application,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from src.bot.ui.formatting import code, h1, ok, warn
from src.bot.ui.keyboards import confirm_kb, lev_kb, side_kb, slip_kb
from src.repositories.user_wallets_repo import get_wallet

logger = logging.getLogger(__name__)

# Flow state keys
OPEN_FLOW = "open_flow"
CLOSE_FLOW = "close_flow"


def register_trades(app: Application, svc_factory):
    """Register trade command handlers with guided flows."""

    # ===== /open command =====
    async def open_cmd(update: Update, context: CallbackContext):
        """Start /open guided flow."""
        context.user_data[OPEN_FLOW] = {"step": "symbol"}
        await update.message.reply_markdown(
            h1("Open Position") + "\nEnter *symbol* (e.g., BTC-USD):"
        )

    # ===== /close command =====
    async def close_cmd(update: Update, context: CallbackContext):
        """Start /close guided flow."""
        context.user_data[CLOSE_FLOW] = {"step": "symbol"}
        await update.message.reply_markdown(
            h1("Close Position") + "\nEnter *symbol* (e.g., BTC-USD):"
        )

    # ===== Text message handler for flow steps =====
    async def text_handler(update: Update, context: CallbackContext):
        """Handle text input for open/close flows."""
        txt = (update.message.text or "").strip().upper()

        # OPEN flow
        if OPEN_FLOW in context.user_data:
            st = context.user_data[OPEN_FLOW]

            if st.get("step") == "symbol":
                st["symbol"] = txt
                st["step"] = "side"
                await update.message.reply_markdown(
                    f"Symbol: {code(txt)}\nChoose *side*:", reply_markup=side_kb()
                )
                return

            if st.get("step") == "collateral":
                try:
                    v = float(txt)
                    assert v > 0
                    st["collateral"] = v
                    st["step"] = "slippage"
                    await update.message.reply_markdown(
                        f"Collateral: *{v:.2f} USDC*\nPick *slippage*:",
                        reply_markup=slip_kb(),
                    )
                except Exception:
                    await update.message.reply_markdown(
                        warn("Enter a positive number for collateral (USDC).")
                    )
                return

        # CLOSE flow
        if CLOSE_FLOW in context.user_data:
            st = context.user_data[CLOSE_FLOW]

            if st.get("step") == "symbol":
                st["symbol"] = txt
                st["step"] = "reduce"
                await update.message.reply_markdown(
                    f"Symbol: {code(txt)}\nEnter *reduce amount* (USDC):"
                )
                return

            if st.get("step") == "reduce":
                try:
                    v = float(txt)
                    assert v > 0
                    st["reduce"] = v
                    st["step"] = "slippage"
                    await update.message.reply_markdown(
                        f"Reduce: *{v:.2f} USDC*\nPick *slippage*:",
                        reply_markup=slip_kb(),
                    )
                except Exception:
                    await update.message.reply_markdown(
                        warn("Enter a positive number for reduce amount (USDC).")
                    )
                return

    # ===== Callback query handler for buttons =====
    async def callback_handler(update: Update, context: CallbackContext):
        """Handle button callbacks for open/close flows."""
        q = update.callback_query
        await q.answer()
        data = q.data

        # OPEN flow
        if OPEN_FLOW in context.user_data:
            st = context.user_data[OPEN_FLOW]

            if data.startswith("side:"):
                st["side"] = data.split(":")[1]
                st["step"] = "lev"
                await q.edit_message_text(
                    f"Side: *{st['side']}*\nChoose *leverage*:",
                    parse_mode="Markdown",
                    reply_markup=lev_kb(),
                )
                return

            if data.startswith("lev:"):
                st["lev"] = int(data.split(":")[1])
                st["step"] = "collateral"
                await q.edit_message_text(
                    f"Leverage: *{st['lev']}x*\nEnter *collateral* (USDC):",
                    parse_mode="Markdown",
                )
                return

            if data.startswith("slip:") and st.get("step") == "slippage":
                st["slip"] = float(data.split(":")[1])
                st["step"] = "confirm"
                await q.edit_message_text(
                    f"*Confirm Open*\n{code(st['symbol'])} • *{st['side']}* • *{st['lev']}x*\nCollateral: *{st['collateral']:.2f}* • Slip: *{st['slip']:.2f}%*",
                    parse_mode="Markdown",
                    reply_markup=confirm_kb("open"),
                )
                return

            if data == "confirm:open" and st.get("step") == "confirm":
                w3, db, svc = svc_factory()
                try:
                    addr = get_wallet(db, context.user.tg_id)
                    if not addr:
                        await q.edit_message_text(
                            warn("No wallet bound. Use /bind <address>."),
                            parse_mode="Markdown",
                        )
                        context.user_data.pop(OPEN_FLOW, None)
                        return

                    txh = svc.open_market(
                        user_id=context.user.tg_id,
                        symbol=st["symbol"],
                        side=st["side"],
                        collateral_usdc=st["collateral"],
                        leverage_x=st["lev"],
                        slippage_pct=st["slip"],
                    )
                    await q.edit_message_text(
                        ok(f"Order sent! Tx: `{txh}`"), parse_mode="Markdown"
                    )
                except Exception as e:
                    logger.error(f"Open market failed: {e}", exc_info=True)
                    await q.edit_message_text(warn(str(e)), parse_mode="Markdown")
                finally:
                    db.close()
                    context.user_data.pop(OPEN_FLOW, None)
                return

        # CLOSE flow
        if CLOSE_FLOW in context.user_data:
            st = context.user_data[CLOSE_FLOW]

            if data.startswith("slip:") and st.get("step") == "slippage":
                st["slip"] = float(data.split(":")[1])
                st["step"] = "confirm"
                await q.edit_message_text(
                    f"*Confirm Close*\n{code(st['symbol'])} • Reduce: *{st['reduce']:.2f}* • Slip: *{st['slip']:.2f}%*",
                    parse_mode="Markdown",
                    reply_markup=confirm_kb("close"),
                )
                return

            if data == "confirm:close" and st.get("step") == "confirm":
                w3, db, svc = svc_factory()
                try:
                    addr = get_wallet(db, context.user.tg_id)
                    if not addr:
                        await q.edit_message_text(
                            warn("No wallet bound. Use /bind <address>."),
                            parse_mode="Markdown",
                        )
                        context.user_data.pop(CLOSE_FLOW, None)
                        return

                    txh = svc.close_market(
                        user_id=context.user.tg_id,
                        symbol=st["symbol"],
                        reduce_usdc=st["reduce"],
                        slippage_pct=st["slip"],
                    )
                    await q.edit_message_text(
                        ok(f"Close sent! Tx: `{txh}`"), parse_mode="Markdown"
                    )
                except Exception as e:
                    logger.error(f"Close market failed: {e}", exc_info=True)
                    await q.edit_message_text(warn(str(e)), parse_mode="Markdown")
                finally:
                    db.close()
                    context.user_data.pop(CLOSE_FLOW, None)
                return

        # Cancel button
        if data == "cancel":
            context.user_data.pop(OPEN_FLOW, None)
            context.user_data.pop(CLOSE_FLOW, None)
            await q.edit_message_text("Cancelled.")
            return

    app.add_handler(CommandHandler("open", open_cmd))
    app.add_handler(CommandHandler("close", close_cmd))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), text_handler))
    app.add_handler(
        CallbackQueryHandler(
            callback_handler, pattern="^(side:|lev:|slip:|confirm:|cancel)"
        )
    )
