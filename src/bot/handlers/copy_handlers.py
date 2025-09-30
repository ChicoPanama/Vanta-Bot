from __future__ import annotations

from decimal import Decimal
from typing import Any

from telegram import Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from src.bot.ui.formatting import fmt_usd
from src.bot.ui.keyboards import kb
from src.config.feature_flags import is_autocopy_allowed
from src.services.copytrading import copy_service


def _cfg_text(tk: str, cfg: dict[str, Any]) -> str:
    lines = [f"*Copy Settings* — `{tk}`"]
    lines.append(
        f"Auto-copy: {'ON' if cfg.get('auto_copy') else 'OFF'}   Notify: {'ON' if cfg.get('notify') else 'OFF'}"
    )
    lines.append(f"Sizing: {cfg.get('sizing_mode')}")
    if cfg.get("sizing_mode") == "FIXED_USD":
        lines.append(f"  Fixed $: {fmt_usd(Decimal(str(cfg.get('fixed_usd', 0))))}")
    elif cfg.get("sizing_mode") == "PCT_EQUITY":
        lines.append(f"  % Equity: {cfg.get('pct_equity')}%")
    lines.append(f"Max Lev: {cfg.get('max_leverage')}")
    lines.append(f"Slippage override: {cfg.get('slippage_override_pct') or '—'}%")
    lines.append(
        f"Per-trade cap: {fmt_usd(Decimal(str(cfg.get('per_trade_cap_usd', 0))))}"
    )
    lines.append(f"Daily cap: {fmt_usd(Decimal(str(cfg.get('daily_cap_usd', 0))))}")
    lines.append(
        f"Loss protection: {'ON' if cfg.get('use_loss_protection') else 'OFF'}"
    )
    lines.append(f"Stop after losses: {cfg.get('stop_after_losses')}")
    lines.append(
        f"Stop after drawdown: {fmt_usd(Decimal(str(cfg.get('stop_after_drawdown_usd', 0))))}"
    )

    # Add active stop rule preview
    if cfg.get("use_loss_protection"):
        stop_rules = []
        if cfg.get("stop_after_losses", 0) > 0:
            stop_rules.append(
                f"⚠️ Loss streak stop @ {cfg.get('stop_after_losses')} losses"
            )
        if cfg.get("stop_after_drawdown_usd", 0) > 0:
            stop_rules.append(
                f"⚠️ Drawdown stop @ {fmt_usd(Decimal(str(cfg.get('stop_after_drawdown_usd'))))}"
            )
        if stop_rules:
            lines.append("")  # Empty line
            lines.extend(stop_rules)

    return "\n".join(lines)


def _cfg_rows(tk: str, cfg: dict[str, Any]):
    rows = [
        [("Auto ⏻", f"cp:toggle:auto:{tk}"), ("Notify 🔔", f"cp:toggle:notify:{tk}")],
    ]

    # Add "Enable Auto-copy" button when auto-copy is OFF and notify is ON
    if not cfg.get("auto_copy") and cfg.get("notify"):
        rows.append([("⚙️ Enable Auto-copy", f"cp:toggle:auto:{tk}")])

    rows.extend(
        [
            [
                ("Sizing: Mirror", f"cp:size:mirror:{tk}"),
                ("Fixed $", f"cp:size:fixed:{tk}"),
                ("% Equity", f"cp:size:pct:{tk}"),
            ],
            [("MaxLev +10", f"cp:lev:up:{tk}"), ("-10", f"cp:lev:down:{tk}")],
            [
                ("Slip 0.5%", f"cp:slip:0.5:{tk}"),
                ("1%", f"cp:slip:1:{tk}"),
                ("2%", f"cp:slip:2:{tk}"),
            ],
            [
                ("PerTrade +100", f"cp:cap_trade:+100:{tk}"),
                ("-100", f"cp:cap_trade:-100:{tk}"),
            ],
            [
                ("DailyCap +1000", f"cp:cap_day:+1000:{tk}"),
                ("-1000", f"cp:cap_day:-1000:{tk}"),
            ],
            [
                ("LossProt ⏻", f"cp:toggle:lossprot:{tk}"),
                ("StopLosses +1", f"cp:streak:+1:{tk}"),
                ("-1", f"cp:streak:-1:{tk}"),
            ],
            [("Drawdown +100", f"cp:dd:+100:{tk}"), ("-100", f"cp:dd:-100:{tk}")],
            [("❌ Unfollow", f"cp:unfollow:{tk}")],
        ]
    )
    # Extra rows for sizing value inputs when required could be added later
    return rows


async def cmd_follow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    if not args:
        await update.effective_chat.send_message(
            "Usage: `/follow <trader_id_or_address>`", parse_mode="Markdown"
        )
        return
    tk = args[0]
    cfg = copy_service.get_cfg(update.effective_user.id, tk)

    # Apply feature flag for auto-copy default
    if cfg.get("auto_copy") is None:  # Only set default if not already configured
        cfg["auto_copy"] = is_autocopy_allowed(update.effective_user.id)

    copy_service.set_cfg(update.effective_user.id, tk, cfg)  # ensures row exists
    await update.effective_chat.send_message(
        _cfg_text(tk, cfg), parse_mode="Markdown", reply_markup=kb(_cfg_rows(tk, cfg))
    )


async def cmd_unfollow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    if not args:
        await update.effective_chat.send_message(
            "Usage: `/unfollow <trader_id_or_address>`", parse_mode="Markdown"
        )
        return
    tk = args[0]
    copy_service.unfollow(update.effective_user.id, tk)
    await update.effective_chat.send_message(
        f"✅ Unfollowed `{tk}`", parse_mode="Markdown"
    )


async def cmd_following(update: Update, context: ContextTypes.DEFAULT_TYPE):
    follows = copy_service.list_follows(update.effective_user.id)
    if not follows:
        await update.effective_chat.send_message(
            "You are not following any traders.\nUse `/follow <id>` or tap *Follow* in /alfa top50.",
            parse_mode="Markdown",
        )
        return
    lines = ["*Following*"]
    rows = []
    for tk, cfg in follows:
        lines.append(
            f"• `{tk}` — Auto: {'ON' if cfg.get('auto_copy') else 'OFF'}, Notify: {'ON' if cfg.get('notify') else 'OFF'}"
        )
        rows.append(
            [("⚙️ Settings", f"cp:open:{tk}"), ("❌ Unfollow", f"cp:unfollow:{tk}")]
        )
    await update.effective_chat.send_message(
        "\n".join(lines), parse_mode="Markdown", reply_markup=kb(rows)
    )


async def cb_copy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    parts = q.data.split(":")
    if len(parts) < 3:
        return
    _, action, *rest = parts

    uid = q.from_user.id

    if action == "open":
        tk = rest[0]
        cfg = copy_service.get_cfg(uid, tk)
        await q.edit_message_text(
            _cfg_text(tk, cfg),
            parse_mode="Markdown",
            reply_markup=kb(_cfg_rows(tk, cfg)),
        )
        return

    if action == "unfollow":
        tk = rest[0]
        copy_service.unfollow(uid, tk)
        await q.edit_message_text(f"✅ Unfollowed `{tk}`", parse_mode="Markdown")
        return

    # mutators
    kind = rest[0]
    tk = rest[1]
    cfg = copy_service.get_cfg(uid, tk)

    if action == "toggle":
        if kind == "auto":
            cfg["auto_copy"] = not cfg.get("auto_copy", False)
        elif kind == "notify":
            cfg["notify"] = not cfg.get("notify", True)
        elif kind == "lossprot":
            cfg["use_loss_protection"] = not cfg.get("use_loss_protection", True)

    elif action == "size":
        if kind == "mirror":
            cfg["sizing_mode"] = "MIRROR"
        elif kind == "fixed":
            cfg["sizing_mode"] = "FIXED_USD"
            cfg["fixed_usd"] = float(cfg.get("fixed_usd", 100.0))
        elif kind == "pct":
            cfg["sizing_mode"] = "PCT_EQUITY"
            cfg["pct_equity"] = float(cfg.get("pct_equity", 1.0))

    elif action == "lev":
        step = 10 if kind == "up" else -10
        cfg["max_leverage"] = max(1, int(cfg.get("max_leverage", 50) + step))

    elif action == "slip":
        cfg["slippage_override_pct"] = (
            float(rest[0]) if kind in ("0.5", "1", "2") else float(kind)
        )

    elif action == "cap_trade":
        delta = float(kind.replace("+", "")) if "+" in kind else float(kind)
        cfg["per_trade_cap_usd"] = max(
            0.0, float(cfg.get("per_trade_cap_usd", 500.0) + delta)
        )

    elif action == "cap_day":
        delta = float(kind.replace("+", "")) if "+" in kind else float(kind)
        cfg["daily_cap_usd"] = max(0.0, float(cfg.get("daily_cap_usd", 5000.0) + delta))

    elif action == "streak":
        delta = int(kind)
        cfg["stop_after_losses"] = max(0, int(cfg.get("stop_after_losses", 5) + delta))

    elif action == "dd":
        delta = float(kind.replace("+", "")) if "+" in kind else float(kind)
        cfg["stop_after_drawdown_usd"] = max(
            0.0, float(cfg.get("stop_after_drawdown_usd", 1000.0) + delta)
        )

    copy_service.set_cfg(uid, tk, cfg)
    await q.edit_message_text(
        _cfg_text(tk, cfg), parse_mode="Markdown", reply_markup=kb(_cfg_rows(tk, cfg))
    )


def register(app):
    app.add_handler(CommandHandler("follow", cmd_follow))
    app.add_handler(CommandHandler("unfollow", cmd_unfollow))
    app.add_handler(CommandHandler("following", cmd_following))
    app.add_handler(CallbackQueryHandler(cb_copy, pattern=r"^cp:"))
