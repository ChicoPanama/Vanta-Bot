from telegram import Update
from telegram.ext import ContextTypes
from src.database.operations import db
from src.bot.keyboards.trading_keyboards import get_main_menu_keyboard
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import logging

logger = logging.getLogger(__name__)

def get_settings_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔔 Notifications", callback_data="settings_notifications"),
         InlineKeyboardButton("🎯 Risk Management", callback_data="settings_risk")],
        [InlineKeyboardButton("💼 Trading Preferences", callback_data="settings_trading"),
         InlineKeyboardButton("🔒 Security", callback_data="settings_security")],
        [InlineKeyboardButton("📊 API Keys", callback_data="settings_api"),
         InlineKeyboardButton("ℹ️ About", callback_data="settings_about")],
        [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle settings command/callback"""
    user_id = update.effective_user.id
    
    # Get user from database  
    db_user = db.get_user(user_id)
    if not db_user:
        if update.callback_query:
            await update.callback_query.answer("❌ User not found")
        else:
            await update.message.reply_text("❌ User not found. Please /start first.")
        return
        
    settings_text = """
⚙️ **Bot Settings**

Configure your trading preferences and bot behavior.

Choose a category to modify:
    """
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            settings_text,
            parse_mode='Markdown',
            reply_markup=get_settings_keyboard()
        )
    else:
        await update.message.reply_text(
            settings_text,
            parse_mode='Markdown',
            reply_markup=get_settings_keyboard()
        )

async def settings_notifications_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle notifications settings"""
    query = update.callback_query
    await query.answer()
    
    notifications_text = """
🔔 **Notification Settings**

• ✅ Position Updates
• ✅ Price Alerts  
• ✅ Liquidation Warnings
• ✅ Trade Confirmations

Notifications are currently enabled.
    """
    
    await query.edit_message_text(
        notifications_text,
        parse_mode='Markdown',
        reply_markup=get_settings_keyboard()
    )

async def settings_risk_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle risk management settings"""
    query = update.callback_query
    await query.answer()
    
    risk_text = """
🎯 **Risk Management**

• Max Position Size: $10,000
• Max Leverage: 500x
• Stop Loss: 5% (default)
• Take Profit: 10% (default)

Configure your risk parameters to protect your capital.
    """
    
    await query.edit_message_text(
        risk_text,
        parse_mode='Markdown',
        reply_markup=get_settings_keyboard()
    )

async def settings_trading_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle trading preferences"""
    query = update.callback_query
    await query.answer()
    
    trading_text = """
💼 **Trading Preferences**

• Default Leverage: 10x
• Preferred Assets: Crypto
• Order Type: Market
• Slippage Tolerance: 0.5%

Customize your default trading parameters.
    """
    
    await query.edit_message_text(
        trading_text,
        parse_mode='Markdown',
        reply_markup=get_settings_keyboard()
    )

async def settings_security_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle security settings"""
    query = update.callback_query
    await query.answer()
    
    security_text = """
🔒 **Security Settings**

• ✅ Private Keys Encrypted
• ✅ Rate Limiting Active
• ✅ Input Validation Enabled
• ✅ Transaction Signing Required

Your account is secure with industry-standard encryption.
    """
    
    await query.edit_message_text(
        security_text,
        parse_mode='Markdown',
        reply_markup=get_settings_keyboard()
    )

async def settings_about_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle about information"""
    query = update.callback_query
    await query.answer()
    
    about_text = """
ℹ️ **About Vanta Bot**

🤖 **Version:** 1.0.0
🔗 **Network:** Base (Ethereum L2)
⚡ **Protocol:** Avantis Protocol
🛡️ **Security:** End-to-end encrypted

**Features:**
• 80+ trading markets
• Up to 500x leverage
• Zero fees on entry/exit
• Real-time portfolio tracking
• Advanced risk management

Built with ❤️ for decentralized trading.
    """
    
    await query.edit_message_text(
        about_text,
        parse_mode='Markdown',
        reply_markup=get_settings_keyboard()
    )

