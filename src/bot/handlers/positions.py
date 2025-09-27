from telegram import Update
from telegram.ext import ContextTypes
from src.database.operations import db
from src.bot.keyboards.trading_keyboards import get_position_action_keyboard, get_main_menu_keyboard
import logging

logger = logging.getLogger(__name__)

async def positions_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle positions command/callback"""
    user_id = update.effective_user.id
    
    # Get user from database  
    db_user = db.get_user(user_id)
    if not db_user:
        await update.callback_query.answer("❌ User not found")
        return
        
    # Get user's open positions
    positions = db.get_user_positions(db_user.id, 'OPEN')
    
    if not positions:
        no_positions_text = """
📈 **Your Positions**

No open positions found.

Start trading with the Trade button!
        """
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                no_positions_text,
                parse_mode='Markdown',
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await update.message.reply_text(
                no_positions_text,
                parse_mode='Markdown',
                reply_markup=get_main_menu_keyboard()
            )
        return
    
    # Format positions
    positions_text = "📈 **Your Open Positions**\n\n"
    
    total_pnl = 0
    for pos in positions:
        pnl_emoji = "🟢" if pos.pnl >= 0 else "🔴"
        total_pnl += pos.pnl
        
        positions_text += f"""
**{pos.symbol}** {'🟢 LONG' if pos.side == 'LONG' else '🔴 SHORT'}
Size: ${pos.size:,.2f} | {pos.leverage}x leverage
Entry: ${pos.entry_price:.4f} | Current: ${pos.current_price:.4f}
PnL: {pnl_emoji} ${pos.pnl:,.2f}
───────────
        """
    
    positions_text += f"\n💰 **Total PnL: ${total_pnl:,.2f}**"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            positions_text,
            parse_mode='Markdown',
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await update.message.reply_text(
            positions_text,
            parse_mode='Markdown',
            reply_markup=get_main_menu_keyboard()
        )
