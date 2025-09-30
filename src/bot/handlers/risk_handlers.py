"""Risk management bot handlers (Phase 7)."""

import logging

from telegram import Update
from telegram.ext import Application, CallbackContext, CommandHandler

from src.bot.ui.formatting import h1, ok, warn
from src.repositories.risk_repo import get_or_create_policy, update_policy

logger = logging.getLogger(__name__)


def register_risk(app: Application, svc_factory):
    """Register risk management command handlers."""

    async def risk(update: Update, context: CallbackContext):
        """View risk policy."""
        w3, db, svc = svc_factory()
        try:
            pol = get_or_create_policy(db, update.effective_user.id)
            await update.message.reply_markdown(
                h1("Risk Policy")
                + f"\nMax Leverage: {pol.max_leverage_x}x"
                + f"\nMax Position: ${pol.max_position_usd_1e6 / 1_000_000:.0f}"
                + f"\nDaily Loss Limit: ${pol.daily_loss_limit_1e6 / 1_000_000:.0f} (0=disabled)"
                + f"\nCircuit Breaker: {'ON' if pol.circuit_breaker else 'OFF'}"
            )
        finally:
            db.close()

    async def setrisk(update: Update, context: CallbackContext):
        """Update risk policy. Usage: /setrisk max_leverage_x=10 circuit_breaker=1"""
        w3, db, svc = svc_factory()
        try:
            if not context.args:
                await update.message.reply_markdown(
                    warn(
                        "Usage: /setrisk field=value [field=value ...]\n"
                        + "Fields: max_leverage_x, max_position_usd_1e6, circuit_breaker (0/1)"
                    )
                )
                return

            # Parse key=value pairs
            fields = {}
            for arg in context.args:
                if "=" not in arg:
                    continue
                k, v = arg.split("=", 1)

                # Convert values
                if k == "circuit_breaker":
                    fields[k] = bool(int(v))
                elif k in {
                    "max_leverage_x",
                    "max_position_usd_1e6",
                    "daily_loss_limit_1e6",
                }:
                    fields[k] = int(v)

            if not fields:
                await update.message.reply_markdown(warn("No valid fields provided."))
                return

            update_policy(db, update.effective_user.id, **fields)
            await update.message.reply_markdown(ok("Risk policy updated."))
        except Exception as e:
            logger.error(f"Failed to update risk policy: {e}")
            await update.message.reply_markdown(warn(f"Error: {e}"))
        finally:
            db.close()

    app.add_handler(CommandHandler("risk", risk))
    app.add_handler(CommandHandler("setrisk", setrisk))
