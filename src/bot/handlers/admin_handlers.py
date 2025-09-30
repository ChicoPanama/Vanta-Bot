from __future__ import annotations

import os
import time

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from src.config.settings import settings
from src.services.copytrading.copy_service import get_cfg, set_cfg
from src.services.copytrading.copy_store import all_trader_keys, users_by_trader
from src.services.trading.execution_service import get_execution_service

STARTED_AT = time.time()
LAST_ERRORS = []  # simple ring buffer in memory


def record_error(msg: str, maxlen: int = 50):
    LAST_ERRORS.append((time.time(), msg))
    if len(LAST_ERRORS) > maxlen:
        del LAST_ERRORS[0]


async def cmd_health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    svc = get_execution_service(settings)
    status = "open" if svc.breaker.is_open() else "ok"
    up = int(time.time() - STARTED_AT)
    await update.effective_chat.send_message(
        f"*Health*\nuptime: {up}s\ncircuit: {status}", parse_mode="Markdown"
    )


async def cmd_diag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_chat.send_message(
        "Diagnostics:\n- PTB v20 async\n- Phases 2–5 installed\n- Phase 6 logging & retries active",
        parse_mode="Markdown",
    )


async def cmd_recent_errors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not LAST_ERRORS:
        await update.effective_chat.send_message("No recent errors.")
        return
    lines = ["*Recent Errors* (most recent last)"]
    for ts, msg in LAST_ERRORS[-10:]:
        lines.append(f"• {time.strftime('%H:%M:%S', time.localtime(ts))} — {msg}")
    await update.effective_chat.send_message("\n".join(lines), parse_mode="Markdown")


async def cmd_latency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t0 = time.time()
    # light-weight ping through quote path if draft exists else noop
    await update.effective_chat.send_message("pong")
    dt = int((time.time() - t0) * 1000)
    await update.effective_chat.send_message(f"latency: {dt}ms")


def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    admin_ids = os.getenv("ADMIN_USER_IDS", "").split(",")
    return str(user_id) in admin_ids


async def cmd_autocopy_off_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to disable auto-copy for all users"""
    if not is_admin(update.effective_user.id):
        await update.effective_chat.send_message("❌ Admin access required.")
        return

    affected_count = 0

    # Get all trader keys
    trader_keys = all_trader_keys()

    # Iterate through all follow configurations
    for trader_key in trader_keys:
        # Get all users following this trader
        from src.services.copytrading.copy_store import users_by_trader

        user_ids = users_by_trader(trader_key)

        for user_id in user_ids:
            cfg = get_cfg(user_id, trader_key)
            if cfg.get("auto_copy", False):
                cfg["auto_copy"] = False
                set_cfg(user_id, trader_key, cfg)
                affected_count += 1

    await update.effective_chat.send_message(
        f"✅ Auto-copy disabled for {affected_count} user-trader pairs.\n"
        f"Affected {len(trader_keys)} traders.",
        parse_mode="Markdown",
    )


async def cmd_autocopy_on_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to enable auto-copy for a specific user"""
    if not is_admin(update.effective_user.id):
        await update.effective_chat.send_message("❌ Admin access required.")
        return

    args = context.args or []
    if not args:
        await update.effective_chat.send_message("Usage: `/autocopy_on_user <user_id>`")
        return

    try:
        target_user_id = int(args[0])
    except ValueError:
        await update.effective_chat.send_message("❌ Invalid user ID. Must be a number.")
        return

    affected_count = 0

    # Get all trader keys
    trader_keys = all_trader_keys()

    # Enable auto-copy for this user across all traders they follow
    for trader_key in trader_keys:
        user_ids = users_by_trader(trader_key)
        if target_user_id in user_ids:
            cfg = get_cfg(target_user_id, trader_key)
            cfg["auto_copy"] = True
            set_cfg(target_user_id, trader_key, cfg)
            affected_count += 1

    await update.effective_chat.send_message(
        f"✅ Auto-copy enabled for user {target_user_id}.\n"
        f"Affected {affected_count} trader follows.",
        parse_mode="Markdown",
    )


async def cmd_autocopy_off_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to disable auto-copy for a specific user"""
    if not is_admin(update.effective_user.id):
        await update.effective_chat.send_message("❌ Admin access required.")
        return

    args = context.args or []
    if not args:
        await update.effective_chat.send_message(
            "Usage: `/autocopy_off_user <user_id>`"
        )
        return

    try:
        target_user_id = int(args[0])
    except ValueError:
        await update.effective_chat.send_message("❌ Invalid user ID. Must be a number.")
        return

    affected_count = 0

    # Get all trader keys
    trader_keys = all_trader_keys()

    # Disable auto-copy for this user across all traders they follow
    for trader_key in trader_keys:
        user_ids = users_by_trader(trader_key)
        if target_user_id in user_ids:
            cfg = get_cfg(target_user_id, trader_key)
            cfg["auto_copy"] = False
            set_cfg(target_user_id, trader_key, cfg)
            affected_count += 1

    await update.effective_chat.send_message(
        f"✅ Auto-copy disabled for user {target_user_id}.\n"
        f"Affected {affected_count} trader follows.",
        parse_mode="Markdown",
    )


def register(app):
    app.add_handler(CommandHandler("health", cmd_health))
    app.add_handler(CommandHandler("diag", cmd_diag))
    app.add_handler(CommandHandler("recent_errors", cmd_recent_errors))
    app.add_handler(CommandHandler("latency", cmd_latency))
    app.add_handler(CommandHandler("autocopy_off_all", cmd_autocopy_off_all))
    app.add_handler(CommandHandler("autocopy_on_user", cmd_autocopy_on_user))
    app.add_handler(CommandHandler("autocopy_off_user", cmd_autocopy_off_user))
