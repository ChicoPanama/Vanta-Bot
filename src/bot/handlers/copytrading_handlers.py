"""
Copy Trading Handlers for Vanta Bot
Telegram bot handlers for copy trading functionality
"""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# Copy trading states (using context.user_data instead of FSM)
CREATING_COPYTRADER = "creating_copytrader"
CONFIGURING_SIZING = "configuring_sizing"
CONFIGURING_RISK = "configuring_risk"
SELECTING_LEADER = "selecting_leader"
SETTING_SIZING_VALUE = "setting_sizing_value"

# Global services (would be injected in real implementation)
copy_executor = None
leaderboard_service = None
market_intelligence = None


def set_services(executor, leaderboard, market_intel):
    """Set the copy trading services"""
    global copy_executor, leaderboard_service, market_intelligence
    copy_executor = executor
    leaderboard_service = leaderboard
    market_intelligence = market_intel


async def copy_trading_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle copy trading command"""
    await update.message.reply_text(
        "📊 **Copy Trading Dashboard**\n\nChoose an option:",
        parse_mode="Markdown",
        reply_markup=get_copy_trading_keyboard(),
    )


async def create_copytrader_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle create copytrader callback"""
    context.user_data["state"] = CREATING_COPYTRADER

    await update.callback_query.edit_message_text(
        "🔧 **Create New Copy Trader**\n\nEnter the trader address you want to copy:",
        parse_mode="Markdown",
        reply_markup=get_back_keyboard(),
    )


async def follow_trader_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle follow trader callback"""
    try:
        if not copy_executor:
            await update.callback_query.edit_message_text(
                "⚠️ Copy executor service not available",
                reply_markup=get_back_keyboard(),
            )
            return

        # Get trader address from callback data
        trader_address = update.callback_query.data.split("_")[
            2
        ]  # follow_trader_0x123...

        user_id = update.effective_user.id

        # Create copy trader relationship
        result = await copy_executor.create_copy_trader(
            user_id=user_id,
            leader_address=trader_address,
            copy_ratio=0.1,  # Default 10% copy ratio
            max_leverage=10,  # Default max leverage
        )

        if result["success"]:
            await update.callback_query.edit_message_text(
                f"✅ **Successfully Started Copy Trading**\n\n"
                f"Leader: {trader_address[:10]}...\n"
                f"Copy Ratio: 10%\n"
                f"Max Leverage: 10x\n\n"
                f"Your trades will now automatically copy this leader's positions.",
                parse_mode="Markdown",
                reply_markup=get_back_keyboard(),
            )
        else:
            await update.callback_query.edit_message_text(
                f"❌ **Failed to Start Copy Trading**\n\n"
                f"Error: {result.get('error', 'Unknown error')}",
                parse_mode="Markdown",
                reply_markup=get_back_keyboard(),
            )

    except Exception as e:
        logger.error(f"Error in follow_trader_handler: {e}")
        await update.callback_query.edit_message_text(
            "❌ Error starting copy trading. Please try again.",
            reply_markup=get_back_keyboard(),
        )


async def my_copytraders_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle my copytraders callback"""
    try:
        if not copy_executor:
            await update.callback_query.edit_message_text(
                "⚠️ Copy executor service not available",
                reply_markup=get_back_keyboard(),
            )
            return

        user_id = update.effective_user.id

        # Get user's copy traders
        copytraders = await copy_executor.get_user_copytraders(user_id)

        if not copytraders:
            await update.callback_query.edit_message_text(
                "📊 **My Copy Traders**\n\n"
                "You are not copying any traders yet.\n"
                "Use the leaderboard to find traders to copy.",
                parse_mode="Markdown",
                reply_markup=get_back_keyboard(),
            )
            return

        text = "📊 **My Copy Traders**\n\n"

        for i, copytrader in enumerate(copytraders[:10], 1):  # Show top 10
            leader_address = copytrader.get("leader_address", "Unknown")[:10] + "..."
            copy_ratio = copytrader.get("copy_ratio", 0)
            status = copytrader.get("status", "Active")
            total_copied = copytrader.get("total_copied", 0)

            text += f"{i}. **{leader_address}**\n"
            text += f"   Ratio: {copy_ratio:.1%} | Status: {status}\n"
            text += f"   Copied: {total_copied} trades\n\n"

        await update.callback_query.edit_message_text(
            text, parse_mode="Markdown", reply_markup=get_copytraders_keyboard()
        )

    except Exception as e:
        logger.error(f"Error in my_copytraders_handler: {e}")
        await update.callback_query.edit_message_text(
            "❌ Error loading copy traders. Please try again.",
            reply_markup=get_back_keyboard(),
        )


async def copy_performance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle copy performance callback"""
    try:
        if not copy_executor:
            await update.callback_query.edit_message_text(
                "⚠️ Copy executor service not available",
                reply_markup=get_back_keyboard(),
            )
            return

        user_id = update.effective_user.id

        # Get copy trading performance
        performance = await copy_executor.get_copy_performance(user_id)

        if not performance:
            await update.callback_query.edit_message_text(
                "📈 **Copy Trading Performance**\n\nNo performance data available yet.",
                parse_mode="Markdown",
                reply_markup=get_back_keyboard(),
            )
            return

        text = "📈 **Copy Trading Performance**\n\n"
        text += f"**Total Copied Trades:** {performance.get('total_trades', 0)}\n"
        text += f"**Successful Copies:** {performance.get('successful_trades', 0)}\n"
        text += f"**Success Rate:** {performance.get('success_rate', 0):.1%}\n"
        text += f"**Total PnL:** ${performance.get('total_pnl', 0):,.2f}\n"
        text += f"**Avg Trade Size:** ${performance.get('avg_trade_size', 0):,.2f}\n\n"

        if performance.get("top_performers"):
            text += "**Top Performing Leaders:**\n"
            for leader in performance["top_performers"][:3]:
                address = leader.get("address", "Unknown")[:10] + "..."
                pnl = leader.get("pnl", 0)
                text += f"• {address}: ${pnl:,.2f}\n"

        await update.callback_query.edit_message_text(
            text, parse_mode="Markdown", reply_markup=get_back_keyboard()
        )

    except Exception as e:
        logger.error(f"Error in copy_performance_handler: {e}")
        await update.callback_query.edit_message_text(
            "❌ Error loading performance data. Please try again.",
            reply_markup=get_back_keyboard(),
        )


async def alfa_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display AI-ranked leaderboard"""
    try:
        if not leaderboard_service:
            await update.callback_query.edit_message_text(
                "⚠️ Leaderboard service not available", reply_markup=get_back_keyboard()
            )
            return

        # Get top traders from leaderboard service
        top_traders = await leaderboard_service.get_top_traders(limit=10)

        if not top_traders:
            await update.callback_query.edit_message_text(
                "📊 **AI Leaderboard**\n\nNo traders available at the moment.",
                parse_mode="Markdown",
                reply_markup=get_back_keyboard(),
            )
            return

        # Format leaderboard
        leaderboard_text = "🏆 **Top AI-Ranked Traders**\n\n"

        for i, trader in enumerate(top_traders[:10], 1):
            address = trader.get("address", "Unknown")[:10] + "..."
            score = trader.get("copyability_score", 0)
            volume = trader.get("last_30d_volume_usd", 0)
            pnl = trader.get("realized_pnl_clean_usd", 0)
            archetype = trader.get("archetype", "Unknown")
            risk_level = trader.get("risk_level", "MED")

            leaderboard_text += f"{i}. **{address}**\n"
            leaderboard_text += f"   Score: {score}/100 | {archetype}\n"
            leaderboard_text += f"   Volume: ${volume:,.0f} | PnL: ${pnl:,.0f}\n"
            leaderboard_text += f"   Risk: {risk_level}\n\n"

        await update.callback_query.edit_message_text(
            leaderboard_text,
            parse_mode="Markdown",
            reply_markup=get_leaderboard_keyboard(),
        )

    except Exception as e:
        logger.error(f"Error in alfa_leaderboard: {e}")
        await update.callback_query.edit_message_text(
            "❌ Error loading leaderboard. Please try again.",
            reply_markup=get_back_keyboard(),
        )


def get_copy_trading_keyboard():
    """Get copy trading main keyboard"""
    keyboard = [
        [InlineKeyboardButton("🏆 AI Leaderboard", callback_data="alfa_leaderboard")],
        [InlineKeyboardButton("👥 My Copy Traders", callback_data="my_copytraders")],
        [InlineKeyboardButton("📈 Copy Performance", callback_data="copy_performance")],
        [
            InlineKeyboardButton(
                "🔧 Create Copy Trader", callback_data="create_copytrader"
            )
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_leaderboard_keyboard():
    """Get leaderboard keyboard with follow buttons"""
    keyboard = []

    # Add follow buttons for top 5 traders (mock data)
    for i in range(1, 6):
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"Follow Trader {i}", callback_data=f"follow_trader_0x{'a' * 40}"
                )
            ]
        )

    keyboard.append(
        [InlineKeyboardButton("🔄 Refresh", callback_data="alfa_leaderboard")]
    )
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="copy_trading")])

    return InlineKeyboardMarkup(keyboard)


def get_copytraders_keyboard():
    """Get copytraders management keyboard"""
    keyboard = [
        [InlineKeyboardButton("🔄 Refresh", callback_data="my_copytraders")],
        [InlineKeyboardButton("🔙 Back", callback_data="copy_trading")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_keyboard():
    """Get back keyboard"""
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="copy_trading")]]
    return InlineKeyboardMarkup(keyboard)
