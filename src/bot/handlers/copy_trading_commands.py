# src/bot/handlers/copy_trading_commands.py
from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, ContextTypes

from src.services.analytics.leaderboard_service import LeaderboardService
from src.services.analytics.position_tracker import PositionTracker
from src.services.copytrading import copy_service

logger = logging.getLogger(__name__)

# Simple in-process singleton registry (replace with DI in your app bootstrap)
_position_tracker: PositionTracker | None = None
_leaderboard_service: LeaderboardService | None = None


def set_position_tracker(tracker: PositionTracker) -> None:
    """Set the position tracker instance"""
    global _position_tracker
    _position_tracker = tracker


def set_leaderboard_service(service: LeaderboardService) -> None:
    """Set the leaderboard service instance"""
    global _leaderboard_service
    _leaderboard_service = service


def get_position_tracker() -> PositionTracker | None:
    """Get the position tracker instance"""
    return _position_tracker


def get_leaderboard_service() -> LeaderboardService | None:
    """Get the leaderboard service instance"""
    return _leaderboard_service


async def cmd_alfa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /alfa top50 - Show AI-powered leaderboard
    """
    text = (update.message.text or "").strip()

    if "top50" not in text.lower():
        await update.message.reply_text(
            "🤖 **ALFA Leaderboard**\n\n"
            "Usage: `/alfa top50`\n"
            "Shows top 50 AI-ranked traders for copy trading.",
            parse_mode="Markdown",
        )
        return

    # Get leaderboard service
    leaderboard_service = get_leaderboard_service()
    if not leaderboard_service:
        await update.message.reply_text(
            "⚠️ Leaderboard service not initialized. Please try again later.",
            parse_mode="Markdown",
        )
        return

    try:
        # Get leaderboard data
        leaders = await leaderboard_service.top_traders(limit=50)

        if not leaders:
            await update.message.reply_text(
                "📊 **ALFA Leaderboard**\n\n"
                "No qualified traders found yet. The system is still indexing data.\n"
                "Try again in a few minutes!",
                parse_mode="Markdown",
            )
            return

        # Format leaderboard message
        message = "🏆 **Top AI-Ranked Traders (ALFA Leaderboard)**\n\n"

        for i, leader in enumerate(leaders[:10], 1):  # Show top 10
            address = leader["address"]
            score = leader.get("copyability_score", 0)
            volume = leader["last_30d_volume_usd"]
            trades = leader["trade_count_30d"]
            archetype = leader.get("archetype", "Unknown")
            risk_level = leader.get("risk_level", "MED")

            message += f"{i}. `{address[:8]}...{address[-6:]}`\n"
            message += f"   📊 Score: {score:.0f}/100\n"
            message += f"   💰 Volume: ${volume:,.0f}\n"
            message += f"   🔄 Trades: {trades:,}\n"
            message += f"   🎯 Type: {archetype}\n"
            message += f"   ⚠️ Risk: {risk_level}\n\n"

        if len(leaders) > 10:
            message += f"... and {len(leaders) - 10} more traders\n\n"

        message += (
            "💡 **How to copy:** Use `/follow <address>` to start copying a trader"
        )

        # Create inline keyboard for quick actions
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="alfa_refresh")],
            [InlineKeyboardButton("📊 My Copy Status", callback_data="copy_status")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            message, parse_mode="Markdown", reply_markup=reply_markup
        )

    except Exception as e:
        logger.error(f"Error getting ALFA leaderboard: {e}")
        await update.message.reply_text(
            "❌ Error loading leaderboard. Please try again later.",
            parse_mode="Markdown",
        )


async def cmd_follow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /follow <leader_address> [size] [risk]
    """
    parts = (update.message.text or "").split()

    if len(parts) < 2:
        await update.message.reply_text(
            "🤝 **Follow Trader**\n\n"
            "Usage: `/follow <leader_address> [size] [risk]`\n\n"
            "**Examples:**\n"
            "• `/follow 0x1234...` (default settings)\n"
            "• `/follow 0x1234... 1000` ($1000 max position)\n"
            "• `/follow 0x1234... 1000 low` (low risk)",
            parse_mode="Markdown",
        )
        return

    leader_address = parts[1]

    # Validate address format
    if not leader_address.startswith("0x") or len(leader_address) != 42:
        await update.message.reply_text(
            "❌ Invalid Ethereum address format. Please check and try again.",
            parse_mode="Markdown",
        )
        return

    # Parse optional parameters
    max_size = 5000  # Default max position size
    risk_level = "medium"  # Default risk level

    if len(parts) > 2:
        try:
            max_size = float(parts[2])
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid size parameter. Please enter a number.",
                parse_mode="Markdown",
            )
            return

    if len(parts) > 3:
        risk = parts[3].lower()
        if risk in ["low", "medium", "high"]:
            risk_level = risk

    # Get position tracker to validate leader
    tracker = get_position_tracker()
    if tracker:
        try:
            leader_stats = await tracker.get_stats(leader_address)
            if not leader_stats:
                await update.message.reply_text(
                    f"⚠️ **Leader Not Found**\n\n"
                    f"Address `{leader_address}` is not in our database yet.\n"
                    f"Try checking the `/alfa top50` leaderboard for verified traders.",
                    parse_mode="Markdown",
                )
                return
        except Exception as e:
            logger.warning(f"Error checking leader stats: {e}")

    user_id = update.effective_user.id

    cfg = copy_service.get_cfg(user_id, leader_address)
    cfg["notify"] = True
    cfg["auto_copy"] = True
    cfg["sizing_mode"] = "FIXED_USD"
    cfg["fixed_usd"] = float(max_size)
    cfg["per_trade_cap_usd"] = float(max_size)
    cfg["daily_cap_usd"] = float(max_size) * 5

    risk_caps = {"low": 5, "medium": 20, "high": 50}
    cfg["max_leverage"] = risk_caps.get(risk_level, cfg.get("max_leverage", 20))

    copy_service.set_cfg(user_id, leader_address, cfg)

    if copy_service.executor_available():
        await update.message.reply_text(
            f"✅ **Following Trader**\n\n"
            f"🎯 Leader: `{leader_address}`\n"
            f"💰 Max Size: ${max_size:,.0f}\n"
            f"⚠️ Risk: {risk_level.title()}\n"
            f"🤖 Auto-copy: Enabled\n\n"
            f"Copy trades will mirror this leader as signals arrive.\n"
            f"Use `/status` to monitor live performance.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            f"⚠️ **Configuration Saved**\n\n"
            f"Leader `{leader_address}` added with max size ${max_size:,.0f}.\n"
            "Auto-copy will activate once the executor service is online.",
            parse_mode="Markdown",
        )


async def cmd_unfollow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /unfollow <leader_address>
    """
    parts = (update.message.text or "").split()

    if len(parts) < 2:
        await update.message.reply_text(
            "🚫 **Unfollow Trader**\n\n"
            "Usage: `/unfollow <leader_address>`\n\n"
            "**Example:**\n"
            "• `/unfollow 0x1234...`",
            parse_mode="Markdown",
        )
        return

    leader_address = parts[1]

    # Validate address format
    if not leader_address.startswith("0x") or len(leader_address) != 42:
        await update.message.reply_text(
            "❌ Invalid Ethereum address format. Please check and try again.",
            parse_mode="Markdown",
        )
        return

    user_id = update.effective_user.id
    followed = {tk for tk, _ in copy_service.list_follows(user_id)}

    if leader_address not in followed:
        await update.message.reply_text(
            f"ℹ️ You are not following `{leader_address}`.", parse_mode="Markdown"
        )
        return

    copy_service.unfollow(user_id, leader_address)

    await update.message.reply_text(
        f"🚫 **Unfollowed Trader**\n\n"
        f"Leader: `{leader_address}`\n\n"
        f"✅ You will no longer copy trades from this trader.\n"
        f"Any open copied positions will remain open.",
        parse_mode="Markdown",
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /status - Show copy trading status and performance
    """
    user_id = update.effective_user.id
    follows = copy_service.list_follows(user_id)

    if not follows:
        await update.message.reply_text(
            "📊 **Copy Trading Status**\n\n"
            "You are not following any traders yet. Use `/follow <address>` to begin.",
            parse_mode="Markdown",
        )
        return

    if not copy_service.executor_available():
        await update.message.reply_text(
            "⚠️ Copy executor is offline. Configurations are saved, but live metrics are unavailable.",
            parse_mode="Markdown",
        )
        return

    try:
        status_bundle = await copy_service.get_status(user_id)
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Error getting copy status: {exc}")
        await update.message.reply_text(
            "❌ Error retrieving copy trading status. Please try again later.",
            parse_mode="Markdown",
        )
        return

    aggregate = status_bundle.get("aggregate") if status_bundle else None
    if not aggregate:
        await update.message.reply_text(
            "⚠️ No execution data available yet. Try again after the next copied trade.",
            parse_mode="Markdown",
        )
        return

    leaders = len(follows)
    active_copies = aggregate.get("active_copies", 0)
    pnl_30d = aggregate.get("pnl_30d")
    if pnl_30d is None:
        pnl_30d = aggregate.get("total_pnl", 0.0)
    volume_30d = aggregate.get("volume_30d")
    if volume_30d is None:
        volume_30d = aggregate.get("total_volume", 0.0)
    win_rate_30d = aggregate.get("win_rate_30d")
    if win_rate_30d is None:
        win_rate_30d = aggregate.get("win_rate", 0.0)
    last_copy = aggregate.get("last_copy_at")

    message_lines = [
        "📊 **Copy Trading Status**",
        "",
        f"🤝 **Active Leaders:** {leaders}",
        f"📈 **Open Copied Positions:** {active_copies}",
        f"💰 **30D Copy P&L:** ${pnl_30d:,.2f}",
        f"🎯 **30D Volume:** ${volume_30d:,.2f}",
        f"📊 **30D Win Rate:** {win_rate_30d:.1f}%",
    ]

    if last_copy:
        message_lines.append(f"🕒 **Last Copy:** {last_copy}")

    leader_stats = status_bundle.get("follows", [])
    if leader_stats:
        message_lines.append("")
        message_lines.append("**Leaders:**")
        for entry in leader_stats[:5]:
            status = entry.get("status", {})
            if not status.get("ok"):
                continue
            pnl = status.get("pnl_30d")
            if pnl is None:
                pnl = status.get("total_pnl", 0.0)
            win_rate = status.get("win_rate_30d")
            if win_rate is None:
                win_rate = status.get("win_rate", 0.0)
            message_lines.append(
                f"• `{entry['trader_key']}` — P&L ${pnl:,.2f}, Win rate {win_rate:.1f}%"
            )

    message_lines.append("")
    message_lines.append("💡 Use `/alfa top50` to discover verified leaders.")

    await update.message.reply_text("\n".join(message_lines), parse_mode="Markdown")


# Callback handlers for inline buttons
async def alfa_refresh_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle ALFA refresh callback"""
    query = update.callback_query
    await query.answer("🔄 Refreshing leaderboard...")

    # Re-run the ALFA command
    await cmd_alfa(update, context)


async def copy_status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle copy status callback"""
    query = update.callback_query
    await query.answer()

    # Re-run the status command
    await cmd_status(update, context)


# Export handlers for registration
copy_trading_handlers = [
    CommandHandler("alfa", cmd_alfa),
    CommandHandler("follow", cmd_follow),
    CommandHandler("unfollow", cmd_unfollow),
    CommandHandler("status", cmd_status),
]
