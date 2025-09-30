from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("💰 Wallet", callback_data="wallet"),
            InlineKeyboardButton("📊 Trade", callback_data="trade"),
        ],
        [
            InlineKeyboardButton("📈 Positions", callback_data="positions"),
            InlineKeyboardButton("📋 Orders", callback_data="orders"),
        ],
        [
            InlineKeyboardButton("🏦 Portfolio", callback_data="portfolio"),
            InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_trading_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🟢 LONG", callback_data="trade_long"),
            InlineKeyboardButton("🔴 SHORT", callback_data="trade_short"),
        ],
        [
            InlineKeyboardButton("📈 Crypto", callback_data="category_crypto"),
            InlineKeyboardButton("💱 Forex", callback_data="category_forex"),
        ],
        [
            InlineKeyboardButton("🥇 Commodities", callback_data="category_commodities"),
            InlineKeyboardButton("📊 Indices", callback_data="category_indices"),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_crypto_assets_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("₿ BTC", callback_data="asset_BTC"),
            InlineKeyboardButton("⟠ ETH", callback_data="asset_ETH"),
        ],
        [
            InlineKeyboardButton("◎ SOL", callback_data="asset_SOL"),
            InlineKeyboardButton("🔺 AVAX", callback_data="asset_AVAX"),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="trade")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_forex_assets_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("EUR/USD", callback_data="asset_EURUSD"),
            InlineKeyboardButton("GBP/USD", callback_data="asset_GBPUSD"),
        ],
        [
            InlineKeyboardButton("USD/JPY", callback_data="asset_USDJPY"),
            InlineKeyboardButton("AUD/USD", callback_data="asset_AUDUSD"),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="trade")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_leverage_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("2x", callback_data="leverage_2"),
            InlineKeyboardButton("5x", callback_data="leverage_5"),
            InlineKeyboardButton("10x", callback_data="leverage_10"),
        ],
        [
            InlineKeyboardButton("25x", callback_data="leverage_25"),
            InlineKeyboardButton("50x", callback_data="leverage_50"),
            InlineKeyboardButton("100x", callback_data="leverage_100"),
        ],
        [
            InlineKeyboardButton("250x", callback_data="leverage_250"),
            InlineKeyboardButton("500x", callback_data="leverage_500"),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="trade")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_position_action_keyboard(position_id: int):
    keyboard = [
        [
            InlineKeyboardButton(
                "📊 Details", callback_data=f"pos_details_{position_id}"
            ),
            InlineKeyboardButton("❌ Close", callback_data=f"pos_close_{position_id}"),
        ],
        [
            InlineKeyboardButton("📈 Add Size", callback_data=f"pos_add_{position_id}"),
            InlineKeyboardButton(
                "🛡️ Set SL/TP", callback_data=f"pos_sltp_{position_id}"
            ),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="positions")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ========================================
# ADVANCED AVANTIS-COMPATIBLE KEYBOARDS
# ========================================


def get_user_type_keyboard():
    """Choose between simple and advanced user interface"""
    keyboard = [
        [
            InlineKeyboardButton("🟢 Simple Trader", callback_data="user_type_simple"),
            InlineKeyboardButton(
                "🔴 Advanced Trader", callback_data="user_type_advanced"
            ),
        ],
        [
            InlineKeyboardButton(
                "ℹ️ What's the difference?", callback_data="user_type_info"
            )
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_simple_trading_keyboard():
    """Simple trading interface for beginners - Avantis compatible"""
    keyboard = [
        [
            InlineKeyboardButton("💰 Wallet", callback_data="wallet"),
            InlineKeyboardButton("📊 Quick Trade", callback_data="quick_trade"),
        ],
        [
            InlineKeyboardButton("📈 My Positions", callback_data="positions"),
            InlineKeyboardButton("📋 Orders", callback_data="orders"),
        ],
        [
            InlineKeyboardButton("🏦 Portfolio", callback_data="portfolio"),
            InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
        ],
        [
            InlineKeyboardButton(
                "🔴 Switch to Advanced", callback_data="switch_to_advanced"
            )
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_advanced_trading_keyboard():
    """Advanced trading interface for professionals - Avantis compatible"""
    keyboard = [
        # Core Trading (Avantis SDK supported)
        [
            InlineKeyboardButton("📊 Trade", callback_data="trade"),
            InlineKeyboardButton("📋 Advanced Orders", callback_data="advanced_orders"),
        ],
        [
            InlineKeyboardButton("📈 Positions", callback_data="positions"),
            InlineKeyboardButton(
                "🔄 Position Management", callback_data="position_mgmt"
            ),
        ],
        # Risk Management (Avantis SDK supported)
        [
            InlineKeyboardButton("🛡️ Risk Management", callback_data="risk_mgmt"),
            InlineKeyboardButton("📊 Analytics", callback_data="analytics"),
        ],
        [
            InlineKeyboardButton("📈 Market Data", callback_data="market_data"),
            InlineKeyboardButton("🔔 Alerts", callback_data="alerts"),
        ],
        # Portfolio & Settings
        [
            InlineKeyboardButton("🏦 Portfolio", callback_data="portfolio"),
            InlineKeyboardButton(
                "⚙️ Advanced Settings", callback_data="advanced_settings"
            ),
        ],
        # Switch to Simple
        [InlineKeyboardButton("🟢 Switch to Simple", callback_data="switch_to_simple")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_quick_trade_keyboard():
    """Quick trade interface for simple users - Avantis compatible"""
    keyboard = [
        [
            InlineKeyboardButton("₿ Bitcoin", callback_data="quick_BTC"),
            InlineKeyboardButton("⟠ Ethereum", callback_data="quick_ETH"),
        ],
        [
            InlineKeyboardButton("◎ Solana", callback_data="quick_SOL"),
            InlineKeyboardButton("🔺 Avalanche", callback_data="quick_AVAX"),
        ],
        [
            InlineKeyboardButton("🟢 LONG", callback_data="quick_long"),
            InlineKeyboardButton("🔴 SHORT", callback_data="quick_short"),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="user_type_simple")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_advanced_orders_keyboard():
    """Advanced order types - Avantis SDK compatible only"""
    keyboard = [
        [
            InlineKeyboardButton("📊 Market Order", callback_data="order_market"),
            InlineKeyboardButton("⏰ Limit Order", callback_data="order_limit"),
        ],
        [
            InlineKeyboardButton("🛑 Stop Order", callback_data="order_stop"),
            InlineKeyboardButton(
                "📈 Conditional Order", callback_data="order_conditional"
            ),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="user_type_advanced")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_position_management_keyboard():
    """Advanced position management - Avantis SDK compatible"""
    keyboard = [
        [
            InlineKeyboardButton("❌ Close All", callback_data="close_all"),
            InlineKeyboardButton(
                "💰 Close Profitable", callback_data="close_profitable"
            ),
        ],
        [
            InlineKeyboardButton("📉 Close Losing", callback_data="close_losing"),
            InlineKeyboardButton("📈 Partial Close", callback_data="partial_close"),
        ],
        [
            InlineKeyboardButton("🛡️ Set Stop Loss", callback_data="set_sl"),
            InlineKeyboardButton("🎯 Set Take Profit", callback_data="set_tp"),
        ],
        [
            InlineKeyboardButton("⚡ Update Leverage", callback_data="update_leverage"),
            InlineKeyboardButton(
                "📊 Position Details", callback_data="position_details"
            ),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="user_type_advanced")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_risk_management_keyboard():
    """Risk management tools - Avantis SDK compatible"""
    keyboard = [
        [
            InlineKeyboardButton("📊 Portfolio Risk", callback_data="portfolio_risk"),
            InlineKeyboardButton("📉 Max Drawdown", callback_data="max_drawdown"),
        ],
        [
            InlineKeyboardButton("🎯 Position Sizing", callback_data="position_sizing"),
            InlineKeyboardButton("📊 Risk Metrics", callback_data="risk_metrics"),
        ],
        [
            InlineKeyboardButton("⚖️ Leverage Limits", callback_data="leverage_limits"),
            InlineKeyboardButton("🚫 Stop Loss Rules", callback_data="stop_loss_rules"),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="user_type_advanced")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_analytics_keyboard():
    """Advanced analytics tools - Avantis compatible"""
    keyboard = [
        [
            InlineKeyboardButton("📈 Performance", callback_data="performance"),
            InlineKeyboardButton("📊 Trade History", callback_data="trade_history"),
        ],
        [
            InlineKeyboardButton("📉 Win Rate", callback_data="win_rate"),
            InlineKeyboardButton("💰 PnL Analysis", callback_data="pnl_analysis"),
        ],
        [
            InlineKeyboardButton(
                "📊 Portfolio Metrics", callback_data="portfolio_metrics"
            ),
            InlineKeyboardButton("🎯 Success Rate", callback_data="success_rate"),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="user_type_advanced")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_market_data_keyboard():
    """Market data and analysis - Avantis SDK compatible"""
    keyboard = [
        [
            InlineKeyboardButton("📊 Real-time Prices", callback_data="realtime_prices"),
            InlineKeyboardButton("📈 Price History", callback_data="price_history"),
        ],
        [
            InlineKeyboardButton("📊 Market Overview", callback_data="market_overview"),
            InlineKeyboardButton("📈 Asset Details", callback_data="asset_details"),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="user_type_advanced")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_alerts_keyboard():
    """Alert management - Avantis compatible"""
    keyboard = [
        [
            InlineKeyboardButton("🔔 Price Alerts", callback_data="price_alerts"),
            InlineKeyboardButton("📊 Position Alerts", callback_data="position_alerts"),
        ],
        [
            InlineKeyboardButton("⚡ PnL Alerts", callback_data="pnl_alerts"),
            InlineKeyboardButton("🚨 Risk Alerts", callback_data="risk_alerts"),
        ],
        [
            InlineKeyboardButton("⚙️ Alert Settings", callback_data="alert_settings"),
            InlineKeyboardButton("📋 Alert History", callback_data="alert_history"),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="user_type_advanced")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_advanced_settings_keyboard():
    """Advanced settings and configuration - Avantis compatible"""
    keyboard = [
        [
            InlineKeyboardButton(
                "🎯 Trading Preferences", callback_data="trading_prefs"
            ),
            InlineKeyboardButton("🛡️ Risk Settings", callback_data="risk_settings"),
        ],
        [
            InlineKeyboardButton("🔔 Notifications", callback_data="notifications"),
            InlineKeyboardButton("📊 Dashboard", callback_data="dashboard"),
        ],
        [
            InlineKeyboardButton("🔐 Security", callback_data="security"),
            InlineKeyboardButton("📈 API Settings", callback_data="api_settings"),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="user_type_advanced")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_user_type_info_keyboard():
    """Information about user types"""
    keyboard = [
        [
            InlineKeyboardButton("🟢 Choose Simple", callback_data="user_type_simple"),
            InlineKeyboardButton(
                "🔴 Choose Advanced", callback_data="user_type_advanced"
            ),
        ],
        [InlineKeyboardButton("🔙 Back to Main", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_tp_sl_keyboard(position_id: int):
    """Take Profit / Stop Loss keyboard - Avantis SDK compatible"""
    keyboard = [
        [
            InlineKeyboardButton(
                "🎯 Set Take Profit", callback_data=f"set_tp_{position_id}"
            ),
            InlineKeyboardButton(
                "🛡️ Set Stop Loss", callback_data=f"set_sl_{position_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                "🔄 Update Both", callback_data=f"update_tp_sl_{position_id}"
            ),
            InlineKeyboardButton(
                "❌ Remove TP/SL", callback_data=f"remove_tp_sl_{position_id}"
            ),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="position_mgmt")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_quick_trade_keyboard():
    """Get quick trade keyboard for simple users"""
    keyboard = [
        [
            InlineKeyboardButton("🟢 LONG", callback_data="quick_long"),
            InlineKeyboardButton("🔴 SHORT", callback_data="quick_short"),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="user_type_simple")],
    ]
    return InlineKeyboardMarkup(keyboard)
