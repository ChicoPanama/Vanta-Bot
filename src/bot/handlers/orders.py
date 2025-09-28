from typing import List, Optional
from telegram import Update
from telegram.ext import ContextTypes

from src.database.operations import db
from src.bot.keyboards.trading_keyboards import get_main_menu_keyboard
from src.bot.middleware.user_middleware import UserMiddleware
from src.bot.constants import USER_NOT_FOUND_MESSAGE, NO_ORDERS_MESSAGE
from src.utils.logging import get_logger

logger = get_logger(__name__)
user_middleware = UserMiddleware()

@user_middleware.require_user
async def orders_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle orders command/callback"""
    db_user = context.user_data['db_user']
    
    try:
        # Get user's pending orders
        orders = await db.list_pending_orders(db_user.id)
        
        if not orders:
            no_orders_text = NO_ORDERS_MESSAGE
            
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
            price_text = f"${order.price:.4f}" if order.price is not None else "Market"

            orders_text += (
                f"{order_type_emoji} **{order.symbol}** {side_emoji} {order.side}\n"
                f"Type: {order.order_type} | Size: ${order.size:,.2f}\n"
                f"Leverage: {order.leverage}x | Price: {price_text}\n"
                f"Status: {order.status}\n"
                "───────────\n"
            )
        
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
