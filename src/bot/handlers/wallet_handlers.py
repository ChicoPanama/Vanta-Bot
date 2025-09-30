"""Wallet management handlers (Phase 5)."""

from telegram import Update
from telegram.ext import Application, CallbackContext, CommandHandler
from web3 import Web3

from src.bot.ui.formatting import fmt_addr, h1, ok, warn
from src.repositories.user_wallets_repo import bind_wallet, get_wallet


def register_wallet(app: Application, svc_factory):
    """Register wallet command handlers."""

    async def bind_(update: Update, context: CallbackContext):
        """Handle /bind command."""
        if not context.args:
            await update.message.reply_markdown(warn("Usage: /bind 0xYourAddress"))
            return

        addr = context.args[0]
        if not Web3.is_address(addr):
            await update.message.reply_markdown(warn("Invalid address."))
            return

        w3, db, svc = svc_factory()
        try:
            rec = bind_wallet(db, context.user.tg_id, addr)
            await update.message.reply_markdown(
                ok(f"Wallet bound: `{fmt_addr(rec.address)}`"), parse_mode="Markdown"
            )
        finally:
            db.close()

    async def balance(update: Update, context: CallbackContext):
        """Handle /balance command."""
        w3, db, svc = svc_factory()
        try:
            addr = get_wallet(db, context.user.tg_id)
            if not addr:
                await update.message.reply_markdown(
                    warn("No wallet bound. Use /bind <address>.")
                )
                return

            wei = w3.eth.get_balance(addr)
            eth_balance = wei / 1e18
            await update.message.reply_markdown(
                h1("Balance") + f"\n{fmt_addr(addr)} • {eth_balance:.6f} ETH"
            )
        finally:
            db.close()

    app.add_handler(CommandHandler("bind", bind_))
    app.add_handler(CommandHandler("balance", balance))
