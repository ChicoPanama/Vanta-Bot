# src/bot/handlers/copy_trading_commands.py
from __future__ import annotations
from typing import Optional, List, Dict, Any
import os
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler

# Import the tracker (adjust import path as needed)
from src.services.analytics.position_tracker import PositionTracker

logger = logging.getLogger(__name__)

# Simple in-process singleton registry (replace with DI in your app bootstrap)
_position_tracker: Optional[PositionTracker] = None

def set_position_tracker(tracker: PositionTracker) -> None:
    """Set the position tracker instance"""
    global _position_tracker
    _position_tracker = tracker

def get_position_tracker() -> Optional[PositionTracker]:
    """Get the position tracker instance"""
    return _position_tracker

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

    # Get position tracker
    tracker = get_position_tracker()
    if not tracker:
        await update.message.reply_text(
            "⚠️ Position tracker not initialized. Please try again later.",
            parse_mode='Markdown'
        )
        return

    try:
        # Get leaderboard data
        leaders = await tracker.get_leaderboard(limit=50)
        
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
            score = leader["copyability_score"]
            volume = leader["last_30d_volume_usd"]
            trades = leader["trade_count_30d"]
            
            message += f"{i}. `{address[:8]}...{address[-6:]}`\n"
            message += f"   📊 Score: {score:.0f}/100\n"
            message += f"   💰 Volume: ${volume:,.0f}\n"
            message += f"   🔄 Trades: {trades:,}\n\n"
        
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
    
    # TODO: Implement actual follow logic with your copy executor
    # For now, just confirm the action
    await update.message.reply_text(
        f"✅ **Following Trader**\n\n"
        f"🎯 Leader: `{leader_address}`\n"
        f"💰 Max Size: ${max_size:,.0f}\n"
        f"⚠️ Risk: {risk_level.title()}\n\n"
        f"🚀 Copy trading will begin automatically when the leader makes trades.\n"
        f"Use `/status` to monitor your copy performance.",
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
    
    # TODO: Implement actual unfollow logic with your copy executor
    # For now, just confirm the action
    await update.message.reply_text(
        f"🚫 **Unfollowed Trader**\n\n"
        f"Leader: `{leader_address}`\n\n"
        f"✅ You will no longer copy trades from this trader.\n"
        f"Any open copied positions will remain open.",
        parse_mode='Markdown'
    )

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /status - Show copy trading status and performance
    """
    # TODO: Implement actual status logic with your copy executor
    # For now, show a placeholder status
    
    await update.message.reply_text(
        "📊 **Copy Trading Status**\n\n"
        "🤝 **Active Leaders:** 0\n"
        "📈 **Open Copied Positions:** 0\n"
        "💰 **30D Copy P&L:** $0.00\n"
        "🎯 **Total Copy Volume:** $0.00\n"
        "📊 **Win Rate:** N/A\n\n"
        "💡 Use `/follow <address>` to start copying a trader from the leaderboard.\n"
        "Use `/alfa top50` to see available traders.",
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
