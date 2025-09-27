from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes

from src.database.operations import db
from src.blockchain.wallet_manager import wallet_manager
from src.bot.keyboards.trading_keyboards import get_main_menu_keyboard
from src.bot.middleware.user_middleware import UserMiddleware
from src.bot.constants import USER_NOT_FOUND_MESSAGE
from src.utils.logging import get_logger

logger = get_logger(__name__)
user_middleware = UserMiddleware()

@user_middleware.require_user
async def wallet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle wallet command and callback"""
    db_user = context.user_data['db_user']
    
    try:
        # Get wallet information
        wallet_info = wallet_manager.get_wallet_info(db_user.wallet_address)
        
        wallet_text = f"""
💰 **Your Wallet**

📍 **Address:** `{wallet_info['address']}`

💎 **Balances:**
• ETH: {wallet_info['eth_balance']:.6f} ETH
• USDC: {wallet_info['usdc_balance']:.2f} USDC

📊 **Trading Power:** ${wallet_info['usdc_balance'] * 500:.2f} (with 500x leverage)

⚠️ **Deposit USDC to start trading**
Send USDC to your wallet address above.
        """
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                wallet_text,
                parse_mode='Markdown',
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await update.message.reply_text(
                wallet_text,
                parse_mode='Markdown',
                reply_markup=get_main_menu_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Error getting wallet info: {e}")
        error_msg = "❌ Error loading wallet information."
        
        if update.callback_query:
            await update.callback_query.answer(error_msg)
        else:
            await update.message.reply_text(error_msg)
