from telegram import Update
from telegram.ext import ContextTypes
from src.database.operations import db
from src.bot.keyboards.trading_keyboards import get_main_menu_keyboard
import logging

logger = logging.getLogger(__name__)

async def orders_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle orders command/callback"""
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
        # Get user's pending orders
        session = db.get_session()
        orders = session.query(db.Order).filter(
            db.Order.user_id == db_user.id,
            db.Order.status == 'PENDING'
        ).all()
        session.close()
        
        if not orders:
            no_orders_text = """
📋 **Your Orders**

No pending orders found.

Create orders through the trading interface!
            """
            
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    no_orders_text,
                    parse_mode='Markdown',
                    reply_markup=get_main_menu_keyboard()
                )
            else:
                await update.message.reply_text(
                    no_orders_text,
                    parse_mode='Markdown',
                    reply_markup=get_main_menu_keyboard()
                )
            return
        
        # Format orders
        orders_text = "📋 **Your Pending Orders**\n\n"
        
        for order in orders:
            order_type_emoji = "📊" if order.order_type == "MARKET" else "⏰" if order.order_type == "LIMIT" else "🛑"
            side_emoji = "🟢" if order.side == "LONG" else "🔴"
            
            orders_text += f"""
{order_type_emoji} **{order.symbol}** {side_emoji} {order.side}
Type: {order.order_type} | Size: ${order.size:,.2f}
Leverage: {order.leverage}x | Price: ${order.price:.4f if order.price else 'Market'}
Status: {order.status}
───────────
            """
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                orders_text,
                parse_mode='Markdown',
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await update.message.reply_text(
                orders_text,
                parse_mode='Markdown',
                reply_markup=get_main_menu_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Error getting orders info: {e}")
        error_msg = "❌ Error loading orders information."
        
        if update.callback_query:
            await update.callback_query.answer(error_msg)
        else:
            await update.message.reply_text(error_msg)

