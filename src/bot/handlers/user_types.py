from telegram import Update
from telegram.ext import ContextTypes
from src.bot.keyboards.trading_keyboards import (
    get_user_type_keyboard, get_simple_trading_keyboard, get_advanced_trading_keyboard
)
import logging

logger = logging.getLogger(__name__)

def get_user_interface_type(context: ContextTypes.DEFAULT_TYPE) -> str:
    """Get current user interface type"""
    return context.user_data.get('user_type', 'simple')

async def user_type_selection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user type selection"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "👋 **Welcome to Vanta Bot!**\n\n"
        "Choose your trading experience level:",
        parse_mode='Markdown',
        reply_markup=get_user_type_keyboard()
    )

async def simple_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle simple user selection"""
    query = update.callback_query
    await query.answer()
    
    # Set user type in context
    context.user_data['user_type'] = 'simple'
    
    await query.edit_message_text(
        "🟢 **Simple Trading Interface**\n\n"
        "Perfect for beginners! Quick and easy trading.\n\n"
        "**Features:**\n"
        "• Quick one-click trading\n"
        "• Basic position management\n"
        "• Simple portfolio view\n"
        "• Easy-to-understand interface\n\n"
        "Start trading with just a few taps!",
        parse_mode='Markdown',
        reply_markup=get_simple_trading_keyboard()
    )

async def advanced_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle advanced user selection"""
    query = update.callback_query
    await query.answer()
    
    # Set user type in context
    context.user_data['user_type'] = 'advanced'
    
    await query.edit_message_text(
        "🔴 **Advanced Trading Interface**\n\n"
        "Professional tools for experienced traders.\n\n"
        "**Features:**\n"
        "• Advanced order types\n"
        "• Professional position management\n"
        "• Risk management tools\n"
        "• Advanced analytics\n"
        "• Real-time market data\n"
        "• Professional settings\n\n"
        "Full suite of professional trading tools!",
        parse_mode='Markdown',
        reply_markup=get_advanced_trading_keyboard()
    )

async def switch_to_advanced_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Switch to advanced interface"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['user_type'] = 'advanced'
    
    await query.edit_message_text(
        "🔴 **Switched to Advanced Interface**\n\n"
        "You now have access to professional trading tools!",
        parse_mode='Markdown',
        reply_markup=get_advanced_trading_keyboard()
    )

async def switch_to_simple_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Switch to simple interface"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['user_type'] = 'simple'
    
    await query.edit_message_text(
        "🟢 **Switched to Simple Interface**\n\n"
        "Back to easy trading for beginners!",
        parse_mode='Markdown',
        reply_markup=get_simple_trading_keyboard()
    )

async def user_type_info_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user type information"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "ℹ️ **User Interface Types**\n\n"
        "**🟢 Simple Interface:**\n"
        "• Perfect for beginners\n"
        "• Quick one-click trading\n"
        "• Basic features only\n"
        "• Easy to understand\n\n"
        "**🔴 Advanced Interface:**\n"
        "• For experienced traders\n"
        "• Professional tools\n"
        "• Advanced features\n"
        "• Full trading suite\n\n"
        "You can switch between interfaces anytime!",
        parse_mode='Markdown',
        reply_markup=get_user_type_keyboard()
    )

async def quick_trade_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quick trade for simple users"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "⚡ **Quick Trade**\n\n"
        "Choose an asset to trade quickly:",
        parse_mode='Markdown',
        reply_markup=get_simple_trading_keyboard()
    )
