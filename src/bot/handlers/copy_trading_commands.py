# src/bot/handlers/copy_trading_commands.py
from __future__ import annotations
from typing import Optional, List, Dict, Any
import os
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler

# Import the services
from src.services.analytics.position_tracker import PositionTracker
from src.services.analytics.leaderboard_service import LeaderboardService
from src.services.copy_trading.copy_executor import CopyExecutor, CopyConfig
from decimal import Decimal

logger = logging.getLogger(__name__)

# Simple in-process singleton registry (replace with DI in your app bootstrap)
_position_tracker: Optional[PositionTracker] = None
_leaderboard_service: Optional[LeaderboardService] = None
_copy_executor: Optional[CopyExecutor] = None

def set_position_tracker(tracker: PositionTracker) -> None:
    """Set the position tracker instance"""
    global _position_tracker
    _position_tracker = tracker

def set_leaderboard_service(service: LeaderboardService) -> None:
    """Set the leaderboard service instance"""
    global _leaderboard_service
    _leaderboard_service = service

def set_copy_executor(executor: CopyExecutor) -> None:
    """Set the copy executor instance"""
    global _copy_executor
    _copy_executor = executor

def get_position_tracker() -> Optional[PositionTracker]:
    """Get the position tracker instance"""
    return _position_tracker

def get_leaderboard_service() -> Optional[LeaderboardService]:
    """Get the leaderboard service instance"""
    return _leaderboard_service

def get_copy_executor() -> Optional[CopyExecutor]:
    """Get the copy executor instance"""
    return _copy_executor

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
            parse_mode='Markdown'
        )
        return

    # Get leaderboard service
    leaderboard_service = get_leaderboard_service()
    if not leaderboard_service:
        await update.message.reply_text(
            "⚠️ Leaderboard service not initialized. Please try again later.",
            parse_mode='Markdown'
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
                parse_mode='Markdown'
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
        
        message += "💡 **How to copy:** Use `/follow <address>` to start copying a trader"
        
        # Create inline keyboard for quick actions
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="alfa_refresh")],
            [InlineKeyboardButton("📊 My Copy Status", callback_data="copy_status")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error getting ALFA leaderboard: {e}")
        await update.message.reply_text(
            "❌ Error loading leaderboard. Please try again later.",
            parse_mode='Markdown'
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
            parse_mode='Markdown'
        )
        return
    
    leader_address = parts[1]
    
    # Validate address format
    if not leader_address.startswith("0x") or len(leader_address) != 42:
        await update.message.reply_text(
            "❌ Invalid Ethereum address format. Please check and try again.",
            parse_mode='Markdown'
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
                parse_mode='Markdown'
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
                    parse_mode='Markdown'
                )
                return
        except Exception as e:
            logger.warning(f"Error checking leader stats: {e}")
    
    # Use copy executor to follow the leader
    copy_executor = get_copy_executor()
    if not copy_executor:
        await update.message.reply_text(
            "⚠️ Copy executor not initialized. Please try again later.",
            parse_mode='Markdown'
        )
        return

    # Create copy configuration
    copy_config = CopyConfig(
        sizing_mode="FIXED_NOTIONAL",
        sizing_value=Decimal(str(max_size)),
        max_slippage_bps=200,  # 2% max slippage
        max_leverage=Decimal("100"),  # Max 100x leverage
        notional_cap=Decimal(str(max_size * 2)),  # Cap at 2x the size
        pair_filters=None  # No pair restrictions for now
    )

    # Follow the leader
    success = await copy_executor.follow(user_id, leader_address, copy_config)
    
    if success:
        await update.message.reply_text(
            f"✅ **Following Trader**\n\n"
            f"🎯 Leader: `{leader_address}`\n"
            f"💰 Max Size: ${max_size:,.0f}\n"
            f"⚠️ Risk: {risk_level.title()}\n\n"
            f"🚀 Copy trading will begin automatically when the leader makes trades.\n"
            f"Use `/status` to monitor your copy performance.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"❌ **Failed to Follow Trader**\n\n"
            f"Could not start following `{leader_address}`.\n"
            f"Please try again later.",
            parse_mode='Markdown'
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
            parse_mode='Markdown'
        )
        return
    
    leader_address = parts[1]
    
    # Validate address format
    if not leader_address.startswith("0x") or len(leader_address) != 42:
        await update.message.reply_text(
            "❌ Invalid Ethereum address format. Please check and try again.",
            parse_mode='Markdown'
        )
        return
    
    # Use copy executor to unfollow the leader
    copy_executor = get_copy_executor()
    if not copy_executor:
        await update.message.reply_text(
            "⚠️ Copy executor not initialized. Please try again later.",
            parse_mode='Markdown'
        )
        return

    success = await copy_executor.unfollow(user_id, leader_address)
    
    if success:
        await update.message.reply_text(
            f"🚫 **Unfollowed Trader**\n\n"
            f"Leader: `{leader_address}`\n\n"
            f"✅ You will no longer copy trades from this trader.\n"
            f"Any open copied positions will remain open.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"❌ **Failed to Unfollow**\n\n"
            f"Could not unfollow `{leader_address}`.\n"
            f"You may not be following this trader.",
            parse_mode='Markdown'
        )

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /status - Show copy trading status and performance
    """
    # Get copy executor to get real status
    copy_executor = get_copy_executor()
    if not copy_executor:
        await update.message.reply_text(
            "⚠️ Copy executor not initialized. Please try again later.",
            parse_mode='Markdown'
        )
        return

    try:
        status_data = await copy_executor.status(user_id)
        
        await update.message.reply_text(
            f"📊 **Copy Trading Status**\n\n"
            f"🤝 **Active Leaders:** {status_data['leaders']}\n"
            f"📈 **Open Copied Positions:** {status_data['open_positions']}\n"
            f"💰 **30D Copy P&L:** ${status_data['copy_pnl_30d']}\n"
            f"🎯 **Total Copy Volume:** ${status_data['total_volume']:.2f}\n"
            f"📊 **Win Rate:** {status_data['win_rate']:.1f}%\n\n"
            f"💡 Use `/follow <address>` to start copying a trader from the leaderboard.\n"
            f"Use `/alfa top50` to see available traders.",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error getting copy status: {e}")
        await update.message.reply_text(
            "❌ Error retrieving copy trading status. Please try again later.",
            parse_mode='Markdown'
        )

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
