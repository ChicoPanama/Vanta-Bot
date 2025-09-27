from typing import Dict, Any
from telegram import Update
from telegram.ext import ContextTypes

from src.database.operations import db
from src.services.analytics import AnalyticsService
from src.bot.keyboards.trading_keyboards import get_main_menu_keyboard
from src.bot.middleware.user_middleware import UserMiddleware
from src.bot.constants import USER_NOT_FOUND_MESSAGE
from src.utils.logging import get_logger

logger = get_logger(__name__)
analytics = AnalyticsService()
user_middleware = UserMiddleware()

@user_middleware.require_user
async def portfolio_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle portfolio command/callback"""
    db_user = context.user_data['db_user']
    
    try:
        # Get user statistics
        stats = analytics.get_user_stats(db_user.id)
        
        # Get current positions
        positions = db.get_user_positions(db_user.id, 'OPEN')
        
        # Calculate portfolio value
        total_open_pnl = sum(pos.pnl for pos in positions)
        
        portfolio_text = f"""
🏦 **Portfolio Analytics**

📊 **Trading Statistics:**
• Total Trades: {stats['total_trades']}
• Win Rate: {stats['win_rate']:.1f}%
• Winning Trades: {stats['winning_trades']}
• Total PnL: ${stats['total_pnl']:,.2f}

📈 **Current Positions:**
• Open Positions: {len(positions)}
• Unrealized PnL: ${total_open_pnl:,.2f}

💰 **Performance:**
• Best Trade: ${max([pos.pnl for pos in positions], default=0):,.2f}
• Worst Trade: ${min([pos.pnl for pos in positions], default=0):,.2f}
        """
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                portfolio_text,
                parse_mode='Markdown',
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await update.message.reply_text(
                portfolio_text,
                parse_mode='Markdown',
                reply_markup=get_main_menu_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Error getting portfolio info: {e}")
        error_msg = "❌ Error loading portfolio information."
        
        if update.callback_query:
            await update.callback_query.answer(error_msg)
        else:
            await update.message.reply_text(error_msg)

