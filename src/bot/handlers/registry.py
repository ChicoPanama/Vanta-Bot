"""
Handler Registry
Centralized registry for all bot handlers with proper organization
"""

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from typing import Dict, List, Tuple, Callable

from src.bot.handlers import (
    start,
    wallet,
    trading,
    positions,
    portfolio,
    orders,
    settings,
    user_types,
    advanced_trading,
    risk_edu_handlers,
    ai_insights_handlers,
)
from src.bot.handlers.copy_trading_commands import (
    copy_trading_handlers, alfa_refresh_callback, copy_status_callback
)
from src.bot.handlers.alfa_handlers import alfa_handlers
from src.bot.handlers.admin_commands import admin_handlers
from src.bot.handlers.avantis_trade_handlers import avantis_handlers
from src.bot.middleware.user_middleware import UserMiddleware
from src.utils.logging import get_logger

logger = get_logger(__name__)


class HandlerRegistry:
    """Registry for organizing and managing all bot handlers"""
    
    def __init__(self):
        self.user_middleware = UserMiddleware()
        self.callback_router = CallbackRouter()
    
    def get_command_handlers(self) -> List[Tuple[str, Callable]]:
        """Get all command handlers with middleware applied"""
        return [
            ("start", start.start_handler),
            ("help", start.help_handler),
            ("wallet", self.user_middleware.require_user(wallet.wallet_handler)),
            ("trade", self.user_middleware.require_user(trading.trade_handler)),
            ("positions", self.user_middleware.require_user(positions.positions_handler)),
            ("portfolio", self.user_middleware.require_user(portfolio.portfolio_handler)),
            ("orders", self.user_middleware.require_user(orders.orders_handler)),
            ("settings", self.user_middleware.require_user(settings.settings_handler)),
            ("analyze", risk_edu_handlers.cmd_analyze),
            ("calc", risk_edu_handlers.cmd_calc),
            ("alpha", ai_insights_handlers.alpha_command),
        ]
    
    def get_conversation_handlers(self) -> List[ConversationHandler]:
        """Get all conversation handlers"""
        # Trading conversation handler
        trade_conversation = ConversationHandler(
            entry_points=[CallbackQueryHandler(trading.leverage_selection_handler, pattern="^leverage_")],
            states={
                trading.SIZE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, trading.size_input_handler)],
                trading.CONFIRM_TRADE: [MessageHandler(filters.TEXT & ~filters.COMMAND, trading.confirm_trade_handler)]
            },
            fallbacks=[CommandHandler("start", start.start_handler)]
        )
        
        return [trade_conversation]
    
    def get_callback_handler(self) -> Callable:
        """Get the main callback query handler"""
        return self.callback_router.route_callback


class CallbackRouter:
    """Routes callback queries to appropriate handlers"""
    
    def __init__(self):
        self.user_middleware = UserMiddleware()
    
    async def route_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Route callback queries to appropriate handlers"""
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        
        # Get current user interface type
        user_type = self.user_middleware.validate_user_interface_type(context)
        
        # Route to appropriate handlers based on callback data
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
        elif callback_data == "ai_insights":
            await ai_insights_handlers.alpha_command(update, context)

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
            await self._handle_quick_trade(update, context, callback_data)
        
        # Settings sub-handlers
        elif callback_data.startswith("settings_"):
            await self._handle_settings(update, context, callback_data)
        
        # Advanced handlers
        elif callback_data.startswith("close_"):
            await self._handle_position_closing(update, context, callback_data)
        elif callback_data in ["position_sizing", "portfolio_risk"]:
            await self._handle_risk_management(update, context, callback_data)
        elif callback_data in ["performance", "trade_history"]:
            await self._handle_analytics(update, context, callback_data)
        
        # Copy trading callbacks
        elif callback_data == "alfa_refresh":
            await alfa_refresh_callback(update, context)
        elif callback_data == "copy_status":
            await copy_status_callback(update, context)
        elif callback_data == "alfa_leaderboard":
            await ai_insights_handlers.alfa_leaderboard(update, context)
        elif callback_data == "ai_market_signal":
            await ai_insights_handlers.ai_market_signal(update, context)
        elif callback_data == "copy_opportunities":
            await ai_insights_handlers.copy_opportunities(update, context)
        elif callback_data == "ai_dashboard":
            await ai_insights_handlers.ai_dashboard(update, context)
        elif callback_data == "market_analysis":
            await ai_insights_handlers.market_analysis(update, context)
        elif callback_data == "trader_analytics":
            await ai_insights_handlers.trader_analytics(update, context)
    
    async def _handle_quick_trade(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
        """Handle quick trade callbacks"""
        query = update.callback_query
        
        if callback_data.startswith(("quick_BTC", "quick_ETH", "quick_SOL", "quick_AVAX")):
            # Extract asset and set up quick trade
            asset = callback_data.split("_")[1]
            context.user_data['quick_asset'] = asset
            from src.bot.keyboards.trading_keyboards import get_quick_trade_keyboard
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
    
    async def _handle_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
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
    
    async def _handle_position_closing(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
        """Handle position closing callbacks"""
        if callback_data == "close_all":
            await advanced_trading.close_all_positions_handler(update, context)
        elif callback_data == "close_profitable":
            await advanced_trading.close_profitable_positions_handler(update, context)
        elif callback_data == "close_losing":
            await advanced_trading.close_losing_positions_handler(update, context)
    
    async def _handle_risk_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
        """Handle risk management callbacks"""
        if callback_data == "position_sizing":
            await advanced_trading.position_sizing_handler(update, context)
        elif callback_data == "portfolio_risk":
            await advanced_trading.portfolio_risk_handler(update, context)
    
    async def _handle_analytics(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
        """Handle analytics callbacks"""
        if callback_data == "performance":
            await advanced_trading.performance_handler(update, context)
        elif callback_data == "trade_history":
            await advanced_trading.trade_history_handler(update, context)
