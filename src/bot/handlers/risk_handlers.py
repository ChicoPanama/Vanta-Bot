from __future__ import annotations

from decimal import Decimal

from telegram import Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from src.bot.ui.formatting import fmt_usd
from src.bot.ui.keyboards import kb
from src.services.risk.risk_calculator import calculator

# Fallback if you don't have a portfolio service yet.
DEFAULT_BAL = Decimal("10000")  # Labeled clearly as a placeholder


def _render_analysis(a: dict) -> str:
    lev = a.get("leverage")
    bal = a.get("account_balance_usd")
    mar = a.get("margin_required_usd")
    liq = a.get("liq_distance_pct")
    q = a.get("quality", {})
    sc = a.get("scenarios", {})

    def _pct(s):
        try:
            return f"{Decimal(s) * 100:.2f}%"
        except:
            return str(s)

    def _usd(s):
        try:
            return fmt_usd(Decimal(s))
        except:
            return str(s)

    lines = [
        "*Risk Analysis* (educational — does not block trades)",
        f"Leverage: {lev}×",
        f"Account (assumed): {_usd(bal)}",
        f"Margin required: {_usd(mar)}",
        f"Approx. distance to liquidation: {_pct(liq)}",
        "",
        f"Quality: {q.get('rating', '—')} ({q.get('score', '—')}/100)",
        f"{q.get('description', '')}",
        "",
        "*Impact Scenarios* (move → est. loss / account impact):",
    ]

    pretty = [
        ("0.5%", "small_0_5pct"),
        ("1.0%", "moderate_1pct"),
        ("2.0%", "stress_2pct"),
        ("5.0%", "crash_5pct"),
        ("10.0%", "black_swan_10pct"),
    ]
    for label, key in pretty:
        row = sc.get(key, {})
        lines.append(
            f"• {label} → {_usd(row.get('loss_usd'))} / {_pct(row.get('account_impact_pct'))}"
        )

    lines.append("")
    lines.append("_All numbers are approximate for education._")
    return "\n".join(lines)


async def cmd_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /analyze <PAIR> <SIZE_USD> <LEV>
    """
    args = context.args or []
    if len(args) < 3:
        await update.effective_chat.send_message(
            "Usage: `/analyze <PAIR> <SIZE_USD> <LEV>`\nExample: `/analyze ETH/USD 1000 25`",
            parse_mode="Markdown",
        )
        return

    pair = args[0].upper()
    size = Decimal(args[1])
    lev = Decimal(args[2])

    # TODO: plug your portfolio balance here when available
    bal = DEFAULT_BAL

    a = calculator.analyze(size, lev, bal, pair)
    await update.effective_chat.send_message(_render_analysis(a), parse_mode="Markdown")


async def cmd_calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /calc <PAIR> <LEV> [risk_pct]
    """
    args = context.args or []
    if len(args) < 2:
        await update.effective_chat.send_message(
            "Usage: `/calc <PAIR> <LEV> [risk_pct]`\nExample: `/calc ETH/USD 25 3`",
            parse_mode="Markdown",
        )
        return

    pair = args[0].upper()
    lev = Decimal(args[1])
    bal = DEFAULT_BAL

    if len(args) > 2:
        # specific risk target
        risk_pct = Decimal(args[2]) / Decimal("100")
        max_loss = bal * risk_pct
        size = (max_loss / Decimal("0.02")).quantize(Decimal("0.01"))
        a = calculator.analyze(size, lev, bal, pair)
        msg = (
            f"*Position Calculator*\n"
            f"Target risk: {risk_pct * 100:.2f}% of account\n"
            f"Suggested size: {fmt_usd(size)} at {lev}×\n\n" + _render_analysis(a)
        )
        await update.effective_chat.send_message(msg, parse_mode="Markdown")
        return

    # show conservative/moderate/aggressive suggestions
    s = calculator.suggest_sizes(bal, lev)
    msg = (
        f"*Position Calculator* — {pair} @ {lev}×\n\n"
        f"Conservative (2%): {fmt_usd(Decimal(s['conservative']))}\n"
        f"Moderate (5%): {fmt_usd(Decimal(s['moderate']))}\n"
        f"Aggressive (10%): {fmt_usd(Decimal(s['aggressive']))}\n\n"
        f"Tip: `/analyze {pair} <size> {lev}` for full analysis."
    )
    await update.effective_chat.send_message(msg, parse_mode="Markdown")


# Inline from the Quote Card
async def cb_view_risk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, _, pair, size_str, lev_str = q.data.split(":")
    # Balance unknown → use labeled assumption; swap in real wallet when available
    bal = DEFAULT_BAL
    a = calculator.analyze(Decimal(size_str), Decimal(lev_str), bal, pair)
    await q.edit_message_text(
        _render_analysis(a),
        parse_mode="Markdown",
        reply_markup=kb([[("⬅️ Back to Quote", "nav:back_to_quote")]]),
    )


def register(app):
    app.add_handler(CommandHandler("analyze", cmd_analyze))
    app.add_handler(CommandHandler("calc", cmd_calc))
    app.add_handler(
        CallbackQueryHandler(cb_view_risk, pattern=r"^qt:viewrisk:.+:.+:.+$")
    )
