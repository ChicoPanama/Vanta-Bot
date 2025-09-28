from telegram import Update
from telegram.ext import ContextTypes
from src.database.operations import db
from src.blockchain.wallet_manager import wallet_manager
from src.blockchain.avantis_client import avantis_client
from src.bot.keyboards.trading_keyboards import (
    get_advanced_trading_keyboard, get_position_management_keyboard,
    get_risk_management_keyboard, get_analytics_keyboard, get_market_data_keyboard,
    get_alerts_keyboard, get_advanced_settings_keyboard, get_tp_sl_keyboard
)
import logging

logger = logging.getLogger(__name__)

async def advanced_orders_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle advanced orders - Avantis SDK compatible"""
    query = update.callback_query
    
    await query.edit_message_text(
        "📋 **Advanced Orders**\n\n"
        "**Avantis Protocol Supported Order Types:**\n\n"
        "📊 **Market Order** - Instant execution at current price\n"
        "⏰ **Limit Order** - Execute at specific price\n"
        "🛑 **Stop Order** - Risk management orders\n"
        "📈 **Conditional Order** - Execute when conditions met\n\n"
        "All orders are executed through Avantis Protocol on Base network.",
        parse_mode='Markdown',
        reply_markup=get_advanced_orders_keyboard()
    )

async def position_management_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle advanced position management - Avantis SDK compatible"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Get user from database
    db_user = await db.get_user(user_id)
    if not db_user:
        await query.answer("❌ User not found")
        return
    
    # Get open positions count
    positions = await db.get_user_positions(db_user.id, 'OPEN')
    
    await query.edit_message_text(
        f"🔄 **Advanced Position Management**\n\n"
        f"**Current Open Positions:** {len(positions)}\n\n"
        f"**Avantis SDK Compatible Features:**\n"
        f"• Close all positions at once\n"
        f"• Close only profitable/losing positions\n"
        f"• Partial position closing\n"
        f"• Set/update Take Profit & Stop Loss\n"
        f"• Update position leverage\n"
        f"• Detailed position analysis\n\n"
        f"All operations use official Avantis SDK methods.",
        parse_mode='Markdown',
        reply_markup=get_position_management_keyboard()
    )

async def risk_management_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle risk management tools - Avantis compatible"""
    query = update.callback_query
    
    await query.edit_message_text(
        "🛡️ **Risk Management**\n\n"
        "**Professional Risk Tools (Avantis Compatible):**\n\n"
        "📊 **Portfolio Risk** - Overall portfolio risk assessment\n"
        "📉 **Max Drawdown** - Maximum loss tracking\n"
        "🎯 **Position Sizing** - Optimal position size calculator\n"
        "📊 **Risk Metrics** - Advanced risk calculations\n"
        "⚖️ **Leverage Limits** - Safe leverage management\n"
        "🚫 **Stop Loss Rules** - Automated risk protection\n\n"
        "All calculations based on Avantis Protocol data.",
        parse_mode='Markdown',
        reply_markup=get_risk_management_keyboard()
    )

async def analytics_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle advanced analytics - Avantis compatible"""
    query = update.callback_query
    
    await query.edit_message_text(
        "📊 **Advanced Analytics**\n\n"
        "**Professional Trading Analytics:**\n\n"
        "📈 **Performance** - Comprehensive performance metrics\n"
        "📊 **Trade History** - Detailed trade analysis\n"
        "📉 **Win Rate** - Success rate tracking\n"
        "💰 **PnL Analysis** - Profit & loss breakdown\n"
        "📊 **Portfolio Metrics** - Portfolio performance\n"
        "🎯 **Success Rate** - Trading success analysis\n\n"
        "All data sourced from Avantis Protocol trades.",
        parse_mode='Markdown',
        reply_markup=get_analytics_keyboard()
    )

async def market_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle market data - Avantis SDK compatible"""
    query = update.callback_query
    
    await query.edit_message_text(
        "📈 **Market Data & Analysis**\n\n"
        "**Real-time Avantis Protocol Data:**\n\n"
        "📊 **Real-time Prices** - Live price feeds\n"
        "📈 **Price History** - Historical price data\n"
        "📊 **Market Overview** - Overall market status\n"
        "📈 **Asset Details** - Detailed asset information\n\n"
        "All market data integrated with Avantis Protocol.",
        parse_mode='Markdown',
        reply_markup=get_market_data_keyboard()
    )

async def alerts_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle alerts management - Avantis compatible"""
    query = update.callback_query
    
    await query.edit_message_text(
        "🔔 **Alert Management**\n\n"
        "**Smart Alerts for Avantis Trading:**\n\n"
        "🔔 **Price Alerts** - Asset price notifications\n"
        "📊 **Position Alerts** - Position status updates\n"
        "⚡ **PnL Alerts** - Profit/loss notifications\n"
        "🚨 **Risk Alerts** - Risk threshold warnings\n"
        "⚙️ **Alert Settings** - Customize alert preferences\n"
        "📋 **Alert History** - Past alert records\n\n"
        "All alerts based on real Avantis Protocol data.",
        parse_mode='Markdown',
        reply_markup=get_alerts_keyboard()
    )

async def advanced_settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle advanced settings - Avantis compatible"""
    query = update.callback_query
    
    await query.edit_message_text(
        "⚙️ **Advanced Settings**\n\n"
        "**Professional Configuration Options:**\n\n"
        "🎯 **Trading Preferences** - Default trading settings\n"
        "🛡️ **Risk Settings** - Risk management parameters\n"
        "🔔 **Notifications** - Alert and notification settings\n"
        "📊 **Dashboard** - Customize your dashboard\n"
        "🔐 **Security** - Security and privacy settings\n"
        "📈 **API Settings** - Avantis Protocol API configuration\n\n"
        "All settings optimized for Avantis Protocol trading.",
        parse_mode='Markdown',
        reply_markup=get_advanced_settings_keyboard()
    )

# Additional advanced handlers for Avantis compatibility

async def close_all_positions_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Close all open positions - Avantis SDK compatible"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    try:
        # Get user from database
        db_user = await db.get_user(user_id)
        if not db_user:
            await query.answer("❌ User not found")
            return
        
        # Get all open positions
        positions = await db.get_user_positions(db_user.id, 'OPEN')
        
        if not positions:
            await query.answer("No open positions to close")
            return
        
        # Decrypt private key
        private_key = wallet_manager.decrypt_private_key(db_user.encrypted_private_key)
        
        closed_count = 0
        for position in positions:
            try:
                # Use Avantis SDK to close position
                tx_hash = avantis_client.close_position(
                    db_user.wallet_address,
                    private_key,
                    position.id
                )
                
                # Update position status in database
                await db.update_position(position.id, status='CLOSED', tx_hash=tx_hash)
                closed_count += 1
                
            except Exception as e:
                logger.error(f"Error closing position {position.id}: {e}")
        
        await query.answer(f"✅ Closed {closed_count} positions successfully")
        await position_management_handler(update, context)
        
    except Exception as e:
        logger.error(f"Error in close_all_positions: {e}")
        await query.answer("❌ Error closing positions")

async def close_profitable_positions_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Close only profitable positions - Avantis SDK compatible"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    try:
        db_user = await db.get_user(user_id)
        if not db_user:
            await query.answer("❌ User not found")
            return
        
        positions = await db.get_user_positions(db_user.id, 'OPEN')
        profitable_positions = [p for p in positions if p.pnl > 0]
        
        if not profitable_positions:
            await query.answer("No profitable positions to close")
            return
        
        private_key = wallet_manager.decrypt_private_key(db_user.encrypted_private_key)
        closed_count = 0
        
        for position in profitable_positions:
            try:
                tx_hash = avantis_client.close_position(
                    db_user.wallet_address,
                    private_key,
                    position.id
                )
                await db.update_position(position.id, status='CLOSED', tx_hash=tx_hash)
                closed_count += 1
            except Exception as e:
                logger.error(f"Error closing profitable position {position.id}: {e}")
        
        await query.answer(f"✅ Closed {closed_count} profitable positions")
        
    except Exception as e:
        logger.error(f"Error in close_profitable_positions: {e}")
        await query.answer("❌ Error closing profitable positions")

async def close_losing_positions_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Close only losing positions - Avantis SDK compatible"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    try:
        db_user = await db.get_user(user_id)
        if not db_user:
            await query.answer("❌ User not found")
            return
        
        positions = await db.get_user_positions(db_user.id, 'OPEN')
        losing_positions = [p for p in positions if p.pnl < 0]
        
        if not losing_positions:
            await query.answer("No losing positions to close")
            return
        
        private_key = wallet_manager.decrypt_private_key(db_user.encrypted_private_key)
        closed_count = 0
        
        for position in losing_positions:
            try:
                tx_hash = avantis_client.close_position(
                    db_user.wallet_address,
                    private_key,
                    position.id
                )
                await db.update_position(position.id, status='CLOSED', tx_hash=tx_hash)
                closed_count += 1
            except Exception as e:
                logger.error(f"Error closing losing position {position.id}: {e}")
        
        await query.answer(f"✅ Closed {closed_count} losing positions")
        
    except Exception as e:
        logger.error(f"Error in close_losing_positions: {e}")
        await query.answer("❌ Error closing losing positions")

async def position_sizing_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Calculate optimal position size - Avantis compatible"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    try:
        db_user = await db.get_user(user_id)
        if not db_user:
            await query.answer("❌ User not found")
            return
        
        wallet_info = wallet_manager.get_wallet_info(db_user.wallet_address)
        account_balance = wallet_info['usdc_balance']
        
        # Risk-based position sizing
        conservative = account_balance * 0.01  # 1% risk
        moderate = account_balance * 0.02      # 2% risk
        aggressive = account_balance * 0.05      # 5% risk
        
        sizing_text = f"""
🎯 **Position Sizing Calculator**

**Account Balance:** ${account_balance:.2f} USDC

**Recommended Position Sizes:**
🟢 **Conservative (1% risk):** ${conservative:.2f}
🟡 **Moderate (2% risk):** ${moderate:.2f}
🔴 **Aggressive (5% risk):** ${aggressive:.2f}

**With 10x Leverage:**
🟢 Conservative: ${conservative * 10:.2f} notional
🟡 Moderate: ${moderate * 10:.2f} notional
🔴 Aggressive: ${aggressive * 10:.2f} notional

*Calculations based on Avantis Protocol risk management*
        """
        
        await query.edit_message_text(
            sizing_text,
            parse_mode='Markdown',
            reply_markup=get_risk_management_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in position_sizing: {e}")
        await query.answer("❌ Error calculating position size")

async def portfolio_risk_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show portfolio risk metrics - Avantis compatible"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    try:
        db_user = await db.get_user(user_id)
        if not db_user:
            await query.answer("❌ User not found")
            return
        
        # Get portfolio risk metrics from Avantis SDK
        risk_metrics = avantis_client.get_portfolio_risk_metrics(db_user.wallet_address)
        
        if not risk_metrics:
            await query.answer("❌ Unable to get risk metrics")
            return
        
        risk_text = f"""
📊 **Portfolio Risk Analysis**

**Portfolio Value:** ${risk_metrics['total_value']:,.2f}
**Total PnL:** ${risk_metrics['total_pnl']:,.2f}
**Max Drawdown:** ${risk_metrics['max_drawdown']:,.2f}
**Leverage Ratio:** {risk_metrics['leverage_ratio']:.2f}x
**Risk Score:** {risk_metrics['risk_score']:.1f}/10
**VaR (95%):** ${risk_metrics['var_95']:,.2f}

**Risk Assessment:**
{'🟢 Low Risk' if risk_metrics['risk_score'] < 3 else '🟡 Medium Risk' if risk_metrics['risk_score'] < 7 else '🔴 High Risk'}

*Data from Avantis Protocol*
        """
        
        await query.edit_message_text(
            risk_text,
            parse_mode='Markdown',
            reply_markup=get_risk_management_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in portfolio_risk: {e}")
        await query.answer("❌ Error getting portfolio risk")

async def performance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show performance metrics - Avantis compatible"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    try:
        db_user = await db.get_user(user_id)
        if not db_user:
            await query.answer("❌ User not found")
            return
        
        from src.services.analytics import Analytics
        analytics = Analytics()
        stats = analytics.get_user_stats(db_user.id)
        
        positions = await db.get_user_positions(db_user.id, 'OPEN')
        unrealized_pnl = sum(pos.pnl for pos in positions)
        
        performance_text = f"""
📈 **Performance Analytics**

**Trading Statistics:**
• Total Trades: {stats['total_trades']}
• Winning Trades: {stats['winning_trades']}
• Win Rate: {stats['win_rate']:.1f}%
• Total Realized PnL: ${stats['total_pnl']:,.2f}

**Current Portfolio:**
• Open Positions: {len(positions)}
• Unrealized PnL: ${unrealized_pnl:,.2f}
• Total Portfolio PnL: ${stats['total_pnl'] + unrealized_pnl:,.2f}

**Performance Metrics:**
• Average Win: ${stats['total_pnl'] / max(stats['winning_trades'], 1):,.2f}
• Profit Factor: {stats['total_pnl'] / max(abs(stats['total_pnl'] - stats['total_pnl']), 1):.2f}

*All data from Avantis Protocol trades*
        """
        
        await query.edit_message_text(
            performance_text,
            parse_mode='Markdown',
            reply_markup=get_analytics_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in performance: {e}")
        await query.answer("❌ Error getting performance data")

async def trade_history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show trade history - Avantis compatible"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    try:
        db_user = await db.get_user(user_id)
        if not db_user:
            await query.answer("❌ User not found")
            return
        
        # Get recent trades from database
        recent_trades = await db.list_recent_closed_positions(db_user.id, limit=10)
        
        if not recent_trades:
            history_text = "📊 **Trade History**\n\nNo completed trades found."
        else:
            history_text = "📊 **Recent Trade History**\n\n"
            for trade in recent_trades:
                pnl_emoji = "🟢" if trade.pnl >= 0 else "🔴"
                history_text += f"""
{pnl_emoji} **{trade.symbol}** {'LONG' if trade.side == 'LONG' else 'SHORT'}
Size: ${trade.size:,.2f} | Leverage: {trade.leverage}x
PnL: {pnl_emoji} ${trade.pnl:,.2f}
────────────────────
                """
        
        await query.edit_message_text(
            history_text,
            parse_mode='Markdown',
            reply_markup=get_analytics_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in trade_history: {e}")
        await query.answer("❌ Error getting trade history")
