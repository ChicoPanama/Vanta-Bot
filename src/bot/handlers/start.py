from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes

from src.database.operations import db
from src.blockchain.wallet_manager import wallet_manager
from src.bot.keyboards.trading_keyboards import get_main_menu_keyboard, get_user_type_keyboard
from src.bot.constants import WELCOME_MESSAGE
from src.utils.logging import get_logger

logger = get_logger(__name__)

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command with user type selection"""
    user = update.effective_user
    
    # Check if user exists in database
    db_user = db.get_user(user.id)
    
    if not db_user:
        # Create new wallet for user
        try:
            wallet = wallet_manager.create_wallet()
            
            # Create user in database
            db_user = db.create_user(
                telegram_id=user.id,
                username=user.username,
                wallet_address=wallet['address'],
                encrypted_private_key=wallet['encrypted_private_key']
            )
            
            welcome_msg = WELCOME_MESSAGE.format(wallet_address=wallet['address'])
            
        except Exception as e:
            logger.error(f"Error creating wallet for user {user.id}: {e}")
            welcome_msg = "❌ Error creating wallet. Please try again."
            
    else:
        # Check if user has already selected interface type
        user_type = context.user_data.get('user_type')
        
        if user_type == 'simple':
            welcome_msg = f"""
🟢 **Simple Trading Interface**

📍 **Your Wallet:** `{db_user.wallet_address}`

Quick and easy trading for beginners.
            """
        elif user_type == 'advanced':
            welcome_msg = f"""
🔴 **Advanced Trading Interface**

📍 **Your Wallet:** `{db_user.wallet_address}`

Professional trading tools for experienced traders.
            """
        else:
            welcome_msg = f"""
👋 **Welcome back!**

📍 **Your Wallet:** `{db_user.wallet_address}`

Choose your preferred trading interface:
            """
    
    # Show appropriate interface based on user type
    user_type = context.user_data.get('user_type')
    
    if user_type == 'simple':
        from src.bot.keyboards.trading_keyboards import get_simple_trading_keyboard
        keyboard = get_simple_trading_keyboard()
    elif user_type == 'advanced':
        from src.bot.keyboards.trading_keyboards import get_advanced_trading_keyboard
        keyboard = get_advanced_trading_keyboard()
    else:
        keyboard = get_user_type_keyboard()
    
    await update.message.reply_text(
        welcome_msg,
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command"""
    help_text = """
🤖 **Vanta Bot Help**

 **Commands:**
/start - Initialize bot and wallet
/wallet - View wallet balance  
/trade - Open trading interface
/positions - View open positions
/portfolio - Portfolio analytics
/analyze - Risk analysis for positions (education)
/calc - Position sizing calculator
/help - Show this help message

**Features:**
✅ Trade 80+ markets (Crypto, Forex, Commodities)
✅ Up to 500x leverage
✅ Zero fees on entry/exit
✅ Loss rebates up to 20%
✅ Real-time portfolio tracking
✅ Simple & Advanced interfaces

**Getting Started:**
1. Deposit USDC to your wallet
2. Choose Simple or Advanced interface
3. Start trading with Avantis Protocol

Need support? Contact @your_support_channel
    """
    
    await update.message.reply_text(
        help_text,
        parse_mode='Markdown',
        reply_markup=get_main_menu_keyboard()
    )
