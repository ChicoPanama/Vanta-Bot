import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ConversationHandler
)
from src.config.settings import config
from src.database.operations import db
from src.bot.handlers.start import start_handler, help_handler
from src.bot.handlers.wallet import wallet_handler
from src.bot.handlers.trading import (
    trade_handler, trade_direction_handler, asset_category_handler,
    asset_selection_handler, leverage_selection_handler, 
    size_input_handler, confirm_trade_handler, SIZE_INPUT, CONFIRM_TRADE
)
from src.bot.handlers.positions import positions_handler
from src.bot.handlers.portfolio import portfolio_handler
from src.bot.handlers.orders import orders_handler
from src.bot.handlers.settings import (
    settings_handler, settings_notifications_handler, settings_risk_handler,
    settings_trading_handler, settings_security_handler, settings_about_handler
)
# New imports for advanced features
from src.bot.handlers.user_types import (
    user_type_selection_handler, simple_user_handler, advanced_user_handler,
    switch_to_advanced_handler, switch_to_simple_handler, user_type_info_handler,
    quick_trade_handler, get_user_interface_type
)
from src.bot.handlers.advanced_trading import (
    advanced_orders_handler, position_management_handler, risk_management_handler,
    analytics_handler, market_data_handler, alerts_handler, advanced_settings_handler
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, config.LOG_LEVEL)
)
logger = logging.getLogger(__name__)

async def callback_query_handler(update: Update, context):
    """Handle all callback queries with user type support"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    # Get current user interface type
    user_type = get_user_interface_type(context)
    
    # Route to appropriate handlers based on user type and callback
    if callback_data == "wallet":
        await wallet_handler(update, context)
    elif callback_data == "trade":
        await trade_handler(update, context)
    elif callback_data == "positions":
        await positions_handler(update, context)
    elif callback_data == "portfolio":
        await portfolio_handler(update, context)
    elif callback_data == "orders":
        await orders_handler(update, context)
    elif callback_data == "settings":
        await settings_handler(update, context)
    elif callback_data == "main_menu":
        await start_handler(update, context)
    
    # User type selection handlers
    elif callback_data == "user_type_simple":
        await simple_user_handler(update, context)
    elif callback_data == "user_type_advanced":
        await advanced_user_handler(update, context)
    elif callback_data == "user_type_info":
        await user_type_info_handler(update, context)
    elif callback_data == "switch_to_advanced":
        await switch_to_advanced_handler(update, context)
    elif callback_data == "switch_to_simple":
        await switch_to_simple_handler(update, context)
    elif callback_data == "quick_trade":
        await quick_trade_handler(update, context)
    
    # Advanced trading handlers (Avantis compatible)
    elif callback_data == "advanced_orders":
        await advanced_orders_handler(update, context)
    elif callback_data == "position_mgmt":
        await position_management_handler(update, context)
    elif callback_data == "risk_mgmt":
        await risk_management_handler(update, context)
    elif callback_data == "analytics":
        await analytics_handler(update, context)
    elif callback_data == "market_data":
        await market_data_handler(update, context)
    elif callback_data == "alerts":
        await alerts_handler(update, context)
    elif callback_data == "advanced_settings":
        await advanced_settings_handler(update, context)
    
    # Trading flow handlers
    elif callback_data.startswith("trade_"):
        await trade_direction_handler(update, context)
    elif callback_data.startswith("category_"):
        await asset_category_handler(update, context)
    elif callback_data.startswith("asset_"):
        await asset_selection_handler(update, context)
    elif callback_data.startswith("leverage_"):
        await leverage_selection_handler(update, context)
    elif callback_data.startswith("quick_"):
        # Handle quick trade for simple users
        if callback_data.startswith("quick_BTC") or callback_data.startswith("quick_ETH") or \
           callback_data.startswith("quick_SOL") or callback_data.startswith("quick_AVAX"):
            # Extract asset and set up quick trade
            asset = callback_data.split("_")[1]
            context.user_data['quick_asset'] = asset
            await query.edit_message_text(
                f"📊 **Quick Trade: {asset}**\n\n"
                f"Choose direction:",
                parse_mode='Markdown',
                reply_markup=get_quick_trade_keyboard()
            )
        elif callback_data.startswith("quick_long") or callback_data.startswith("quick_short"):
            # Handle quick trade direction
            direction = "LONG" if "long" in callback_data else "SHORT"
            context.user_data['quick_direction'] = direction
            await query.edit_message_text(
                f"📊 **Quick Trade Setup**\n\n"
                f"Asset: {context.user_data.get('quick_asset', 'BTC')}\n"
                f"Direction: {direction}\n"
                f"Leverage: 10x (recommended)\n"
                f"Size: $100 (recommended)\n\n"
                f"Type 'confirm' to execute or 'cancel' to abort:",
                parse_mode='Markdown'
            )
    
    # Settings sub-handlers
    elif callback_data.startswith("settings_"):
        if callback_data == "settings_notifications":
            await settings_notifications_handler(update, context)
        elif callback_data == "settings_risk":
            await settings_risk_handler(update, context)
        elif callback_data == "settings_trading":
            await settings_trading_handler(update, context)
        elif callback_data == "settings_security":
            await settings_security_handler(update, context)
        elif callback_data == "settings_about":
            await settings_about_handler(update, context)
    
    # Advanced position management handlers
    elif callback_data.startswith("close_"):
        if callback_data == "close_all":
            await close_all_positions_handler(update, context)
        elif callback_data == "close_profitable":
            await close_profitable_positions_handler(update, context)
        elif callback_data == "close_losing":
            await close_losing_positions_handler(update, context)
    
    # Risk management handlers
    elif callback_data == "position_sizing":
        await position_sizing_handler(update, context)
    elif callback_data == "portfolio_risk":
        await portfolio_risk_handler(update, context)
    
    # Analytics handlers
    elif callback_data == "performance":
        await performance_handler(update, context)
    elif callback_data == "trade_history":
        await trade_history_handler(update, context)

def main():
    """Start the bot with user type support"""
    # Create database tables
    db.create_tables()
    
    # Create application
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    
    # Add command handlers
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("wallet", wallet_handler))
    app.add_handler(CommandHandler("trade", trade_handler))
    app.add_handler(CommandHandler("positions", positions_handler))
    app.add_handler(CommandHandler("portfolio", portfolio_handler))
    app.add_handler(CommandHandler("orders", orders_handler))
    app.add_handler(CommandHandler("settings", settings_handler))
    
    # Add conversation handler for trading
    trade_conversation = ConversationHandler(
        entry_points=[CallbackQueryHandler(leverage_selection_handler, pattern="^leverage_")],
        states={
            SIZE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, size_input_handler)],
            CONFIRM_TRADE: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_trade_handler)]
        },
        fallbacks=[CommandHandler("start", start_handler)]
    )
    app.add_handler(trade_conversation)
    
    # Add callback query handler
    app.add_handler(CallbackQueryHandler(callback_query_handler))
    
    # Start polling
    logger.info("Starting Vanta Bot with Advanced Features...")
    app.run_polling()

if __name__ == "__main__":
    main()
