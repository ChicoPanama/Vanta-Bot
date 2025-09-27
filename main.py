"""
Vanta Bot - Main Entry Point
Professional Telegram trading bot for the Avantis Protocol on Base network
"""

import asyncio
import logging
import os
from sqlalchemy import create_engine
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler

from src.config.settings import config
from src.database.operations import db
from src.bot.handlers import (
    start, wallet, trading, positions, portfolio, orders, settings,
    user_types, advanced_trading
)
from src.bot.handlers.copy_trading_commands import (
    copy_trading_handlers, alfa_refresh_callback, copy_status_callback
)
from src.bot.handlers.alfa_handlers import alfa_handlers
from src.bot.handlers.admin_commands import admin_handlers
from src.bot.keyboards.trading_keyboards import get_quick_trade_keyboard
from src.services.analytics.position_tracker import PositionTracker
from src.services.indexers.avantis_indexer import AvantisIndexer
from src.services.contracts.avantis_registry import initialize_registry, resolve_avantis_vault

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, config.LOG_LEVEL)
)
logger = logging.getLogger(__name__)


def create_application() -> Application:
    """Create and configure the Telegram bot application"""
    # Create database tables
    db.create_tables()
    
    # Create application
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    
    # Add command handlers
    app.add_handler(CommandHandler("start", start.start_handler))
    app.add_handler(CommandHandler("help", start.help_handler))
    app.add_handler(CommandHandler("wallet", wallet.wallet_handler))
    app.add_handler(CommandHandler("trade", trading.trade_handler))
    app.add_handler(CommandHandler("positions", positions.positions_handler))
    app.add_handler(CommandHandler("portfolio", portfolio.portfolio_handler))
    app.add_handler(CommandHandler("orders", orders.orders_handler))
    app.add_handler(CommandHandler("settings", settings.settings_handler))
    
    # Add copy trading command handlers
    for handler in copy_trading_handlers:
        app.add_handler(handler)
    
    # Add alfa command handlers
    for handler in alfa_handlers:
        app.add_handler(handler)
    
    # Add admin command handlers
    for handler in admin_handlers:
        app.add_handler(handler)
    
    # Add conversation handler for trading
    trade_conversation = ConversationHandler(
        entry_points=[CallbackQueryHandler(trading.leverage_selection_handler, pattern="^leverage_")],
        states={
            trading.SIZE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, trading.size_input_handler)],
            trading.CONFIRM_TRADE: [MessageHandler(filters.TEXT & ~filters.COMMAND, trading.confirm_trade_handler)]
        },
        fallbacks=[CommandHandler("start", start.start_handler)]
    )
    app.add_handler(trade_conversation)
    
    # Add callback query handler
    app.add_handler(CallbackQueryHandler(callback_query_handler))
    
    return app


async def callback_query_handler(update, context):
    """Handle all callback queries with user type support"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    # Get current user interface type
    user_type = user_types.get_user_interface_type(context)
    
    # Route to appropriate handlers
    await route_callback(callback_data, update, context, user_type)


async def route_callback(callback_data: str, update, context, user_type: str):
    """Route callback queries to appropriate handlers"""
    
    # Main menu handlers
    if callback_data == "wallet":
        await wallet.wallet_handler(update, context)
    elif callback_data == "trade":
        await trading.trade_handler(update, context)
    elif callback_data == "positions":
        await positions.positions_handler(update, context)
    elif callback_data == "portfolio":
        await portfolio.portfolio_handler(update, context)
    elif callback_data == "orders":
        await orders.orders_handler(update, context)
    elif callback_data == "settings":
        await settings.settings_handler(update, context)
    elif callback_data == "main_menu":
        await start.start_handler(update, context)
    
    # User type selection handlers
    elif callback_data == "user_type_simple":
        await user_types.simple_user_handler(update, context)
    elif callback_data == "user_type_advanced":
        await user_types.advanced_user_handler(update, context)
    elif callback_data == "user_type_info":
        await user_types.user_type_info_handler(update, context)
    elif callback_data == "switch_to_advanced":
        await user_types.switch_to_advanced_handler(update, context)
    elif callback_data == "switch_to_simple":
        await user_types.switch_to_simple_handler(update, context)
    elif callback_data == "quick_trade":
        await user_types.quick_trade_handler(update, context)
    
    # Advanced trading handlers
    elif callback_data == "advanced_orders":
        await advanced_trading.advanced_orders_handler(update, context)
    elif callback_data == "position_mgmt":
        await advanced_trading.position_management_handler(update, context)
    elif callback_data == "risk_mgmt":
        await advanced_trading.risk_management_handler(update, context)
    elif callback_data == "analytics":
        await advanced_trading.analytics_handler(update, context)
    elif callback_data == "market_data":
        await advanced_trading.market_data_handler(update, context)
    elif callback_data == "alerts":
        await advanced_trading.alerts_handler(update, context)
    elif callback_data == "advanced_settings":
        await advanced_trading.advanced_settings_handler(update, context)
    
    # Trading flow handlers
    elif callback_data.startswith("trade_"):
        await trading.trade_direction_handler(update, context)
    elif callback_data.startswith("category_"):
        await trading.asset_category_handler(update, context)
    elif callback_data.startswith("asset_"):
        await trading.asset_selection_handler(update, context)
    elif callback_data.startswith("leverage_"):
        await trading.leverage_selection_handler(update, context)
    elif callback_data.startswith("quick_"):
        await handle_quick_trade(update, context, callback_data)
    
    # Settings sub-handlers
    elif callback_data.startswith("settings_"):
        await handle_settings(update, context, callback_data)
    
    # Advanced handlers
    elif callback_data.startswith("close_"):
        await handle_position_closing(update, context, callback_data)
    elif callback_data in ["position_sizing", "portfolio_risk"]:
        await handle_risk_management(update, context, callback_data)
    elif callback_data in ["performance", "trade_history"]:
        await handle_analytics(update, context, callback_data)
    
    # Copy trading callbacks
    elif callback_data == "alfa_refresh":
        await alfa_refresh_callback(update, context)
    elif callback_data == "copy_status":
        await copy_status_callback(update, context)


async def handle_quick_trade(update, context, callback_data: str):
    """Handle quick trade callbacks"""
    query = update.callback_query
    
    if callback_data.startswith(("quick_BTC", "quick_ETH", "quick_SOL", "quick_AVAX")):
        # Extract asset and set up quick trade
        asset = callback_data.split("_")[1]
        context.user_data['quick_asset'] = asset
        await query.edit_message_text(
            f"📊 **Quick Trade: {asset}**\n\n"
            f"Choose direction:",
            parse_mode='Markdown',
            reply_markup=get_quick_trade_keyboard()
        )
    elif callback_data.startswith(("quick_long", "quick_short")):
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


async def handle_settings(update, context, callback_data: str):
    """Handle settings callbacks"""
    if callback_data == "settings_notifications":
        await settings.settings_notifications_handler(update, context)
    elif callback_data == "settings_risk":
        await settings.settings_risk_handler(update, context)
    elif callback_data == "settings_trading":
        await settings.settings_trading_handler(update, context)
    elif callback_data == "settings_security":
        await settings.settings_security_handler(update, context)
    elif callback_data == "settings_about":
        await settings.settings_about_handler(update, context)


async def handle_position_closing(update, context, callback_data: str):
    """Handle position closing callbacks"""
    if callback_data == "close_all":
        await advanced_trading.close_all_positions_handler(update, context)
    elif callback_data == "close_profitable":
        await advanced_trading.close_profitable_positions_handler(update, context)
    elif callback_data == "close_losing":
        await advanced_trading.close_losing_positions_handler(update, context)


async def handle_risk_management(update, context, callback_data: str):
    """Handle risk management callbacks"""
    if callback_data == "position_sizing":
        await advanced_trading.position_sizing_handler(update, context)
    elif callback_data == "portfolio_risk":
        await advanced_trading.portfolio_risk_handler(update, context)


async def handle_analytics(update, context, callback_data: str):
    """Handle analytics callbacks"""
    if callback_data == "performance":
        await advanced_trading.performance_handler(update, context)
    elif callback_data == "trade_history":
        await advanced_trading.trade_history_handler(update, context)


async def start_background_services():
    """Start background services like position tracker and indexer"""
    try:
        # Initialize contract registry and resolve vault address
        if (hasattr(config, 'AVANTIS_TRADING_CONTRACT') and 
            config.AVANTIS_TRADING_CONTRACT and 
            hasattr(config, 'BASE_RPC_URL') and 
            config.BASE_RPC_URL):
            
            from web3 import Web3
            
            # Initialize Web3 connection
            w3 = Web3(Web3.HTTPProvider(config.BASE_RPC_URL))
            if not w3.is_connected():
                logger.error("❌ Failed to connect to Base RPC")
                return
            
            # Initialize contract registry
            registry = initialize_registry(w3, config.AVANTIS_TRADING_CONTRACT)
            
            # Resolve vault address
            try:
                vault_address = await resolve_avantis_vault()
                if vault_address:
                    os.environ["AVANTIS_VAULT_CONTRACT"] = vault_address
                    logger.info(f"✅ Resolved Avantis Vault: {vault_address}")
                else:
                    logger.warning("⚠️ Could not resolve vault address from Trading Proxy")
                    logger.info("Bot will continue without vault contract (trading features will work)")
            except Exception as e:
                logger.warning(f"⚠️ Error resolving vault address: {e}")
                logger.info("Bot will continue without vault contract (trading features will work)")
        
        # Initialize position tracker if database URL is available
        if hasattr(config, 'DATABASE_URL') and config.DATABASE_URL:
            engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)
            tracker = PositionTracker(engine=engine)
            
            # Set tracker for handlers
            from src.bot.handlers.copy_trading_commands import set_position_tracker
            set_position_tracker(tracker)
            
            # Start position tracker as background task
            asyncio.create_task(tracker.start())
            logger.info("✅ Position tracker started")
        
        # Initialize Avantis indexer if contracts are configured
        if (hasattr(config, 'AVANTIS_TRADING_CONTRACT') and 
            config.AVANTIS_TRADING_CONTRACT and 
            hasattr(config, 'BASE_RPC_URL') and 
            config.BASE_RPC_URL):
            
            from sqlalchemy.orm import sessionmaker
            
            # Set up database session factory for indexer
            engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)
            Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
            
            indexer = AvantisIndexer()
            indexer.set_db_session_factory(Session)
            
            # Get latest block and do initial backfill
            w3 = indexer.w3_http
            latest = w3.eth.block_number
            backfill_range = int(os.getenv("INDEXER_BACKFILL_RANGE", "50000"))
            backfill_from = max(0, latest - backfill_range)
            
            logger.info(f"🔄 Starting indexer backfill from block {backfill_from} to {latest}")
            
            # Do initial backfill, then start tailing
            asyncio.create_task(run_indexer_with_backfill(indexer, backfill_from, latest))
            logger.info("✅ Avantis indexer started with backfill")
            
    except Exception as e:
        logger.error(f"❌ Error starting background services: {e}")

async def run_indexer_with_backfill(indexer, from_block, to_block):
    """Run indexer with backfill then tail follow"""
    try:
        await indexer.backfill(from_block, to_block)
        logger.info("✅ Backfill completed, starting tail following...")
        await indexer.tail_follow(start_block=to_block)
    except Exception as e:
        logger.error(f"❌ Indexer error: {e}")

def main():
    """Start the bot"""
    app = create_application()
    
    # Start background services
    asyncio.create_task(start_background_services())
    
    logger.info("Starting Vanta Bot with Advanced Features...")
    app.run_polling()


if __name__ == "__main__":
    main()