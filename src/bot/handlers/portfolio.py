from telegram import Update
from telegram.ext import ContextTypes
from src.database.operations import db
from src.services.analytics import Analytics
from src.bot.keyboards.trading_keyboards import get_main_menu_keyboard
import logging

logger = logging.getLogger(__name__)

analytics = Analytics()

async def portfolio_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle portfolio command/callback"""
    user_id = update.effective_user.id
    
    # Get user from database  
    db_user = db.get_user(user_id)
    if not db_user:
        if update.callback_query:
            await update.callback_query.answer("❌ User not found")
        else:
            await update.message.reply_text("❌ User not found. Please /start first.")
        return
        
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

