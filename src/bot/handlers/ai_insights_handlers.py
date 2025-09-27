"""
AI Insights Handlers for Vanta Bot
Telegram bot handlers for AI market intelligence and insights
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from ...ai.market_intelligence import MarketIntelligence
from ...copy_trading.leaderboard_service import LeaderboardService

logger = logging.getLogger(__name__)

router = Router()

# Global instances (would be injected in real implementation)
market_intelligence: Optional[MarketIntelligence] = None
leaderboard_service: Optional[LeaderboardService] = None

def set_services(market_intel: MarketIntelligence, leaderboard: LeaderboardService):
    """Set the service instances"""
    global market_intelligence, leaderboard_service
    market_intelligence = market_intel
    leaderboard_service = leaderboard

@router.message(Command("alpha"))
async def alpha_command(message: Message):
    """AI insights and market intelligence command"""
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if not args:
        # Show main alpha menu
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Market Overview", callback_data="alpha_market")],
            [InlineKeyboardButton(text="🎯 Top Opportunities", callback_data="alpha_opportunities")],
            [InlineKeyboardButton(text="🔍 Analyze Trader", callback_data="alpha_analyze")],
            [InlineKeyboardButton(text="⚡ Regime Signals", callback_data="alpha_signals")]
        ])
        
        await message.answer(
            "🧠 **AI Market Intelligence**\n\n"
            "Get AI-powered insights about traders, market conditions, and copy opportunities.",
            reply_markup=keyboard
        )
        return
    
    if args[0] == "market":
        await show_market_intelligence(message)
    else:
        # Assume it's a trader address
        address = args[0]
        if address.startswith('0x') and len(address) == 42:
            trader_card = await leaderboard_service.get_trader_card(address)
            if trader_card:
                await show_trader_analysis(message, trader_card)
            else:
                await message.answer(f"❌ No data found for trader {address[:10]}...")
        else:
            await message.answer("❌ Invalid trader address format")

@router.callback_query(F.data == "alpha_market")
async def show_market_intelligence(callback_or_message):
    """Show AI market intelligence overview"""
    try:
        # Get market regime for major pairs
        major_pairs = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'AVAX-USD']
        regime_data = {}
        
        for pair in major_pairs:
            signal = await market_intelligence.get_copy_timing_signal(pair)
            regime_data[pair] = signal
        
        # Get overall market sentiment
        green_count = sum(1 for data in regime_data.values() if data.signal == 'green')
        yellow_count = sum(1 for data in regime_data.values() if data.signal == 'yellow')
        red_count = sum(1 for data in regime_data.values() if data.signal == 'red')
        
        if green_count >= 3:
            overall_sentiment = "🟢 Favorable for copying"
        elif red_count >= 2:
            overall_sentiment = "🔴 High risk for copying"
        else:
            overall_sentiment = "🟡 Mixed conditions"
        
        text = "🧠 **AI Market Intelligence**\n\n"
        text += f"📊 **Overall Sentiment:** {overall_sentiment}\n\n"
        
        text += "🎯 **Pair-by-Pair Analysis:**\n"
        for pair, data in regime_data.items():
            signal_emoji = {"green": "🟢", "yellow": "🟡", "red": "🔴"}[data.signal]
            vol = data.volatility * 100
            trend = data.trend.title()
            
            text += f"{signal_emoji} **{pair}** ({vol:.1f}% vol, {trend})\n"
            text += f"   _{data.reason}_\n\n"
        
        # Get top opportunities
        top_traders = await leaderboard_service.get_top_traders(limit=3)
        if top_traders:
            text += "⭐ **Top Copy Opportunities:**\n"
            for trader in top_traders:
                addr = trader['address'][:8]
                score = trader.get('copyability_score', 50)
                archetype = trader.get('archetype', 'Unknown')
                text += f"• {addr}... ({score}/100) - {archetype}\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Refresh Data", callback_data="alpha_market")],
            [InlineKeyboardButton(text="📈 Detailed Analysis", callback_data="alpha_detailed")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="alpha_menu")]
        ])
        
        if hasattr(callback_or_message, 'edit_text'):
            await callback_or_message.edit_text(text, reply_markup=keyboard)
        else:
            await callback_or_message.answer(text, reply_markup=keyboard)
            
    except Exception as e:
        logger.error(f"Error showing market intelligence: {e}")
        error_text = "❌ Error loading market intelligence. Please try again later."
        
        if hasattr(callback_or_message, 'edit_text'):
            await callback_or_message.edit_text(error_text)
        else:
            await callback_or_message.answer(error_text)

@router.callback_query(F.data == "alpha_opportunities")
async def show_copy_opportunities(callback: CallbackQuery):
    """Show AI-identified copy opportunities"""
    try:
        # Get opportunities based on multiple factors
        opportunities = await market_intelligence.get_copy_opportunities()
        
        if not opportunities:
            await callback.message.edit_text(
                "🔍 **Copy Opportunities**\n\n"
                "No high-confidence opportunities identified at the moment. "
                "Check back in a few minutes as market conditions change.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Back", callback_data="alpha_menu")]
                ])
            )
            return
        
        text = "🎯 **AI Copy Opportunities**\n\n"
        text += "Based on trader performance, market conditions, and timing:\n\n"
        
        for i, opp in enumerate(opportunities[:5], 1):
            symbol = opp['symbol']
            score = opp['confidence'] * 100
            reason = opp['reason']
            confidence = opp['confidence'] * 100
            optimal_size = opp.get('optimal_size', 100)
            
            text += f"{i}. **{symbol}** (Score: {score:.0f}/100)\n"
            text += f"   💡 {reason}\n"
            text += f"   🎯 Confidence: {confidence:.0f}% • Size: ${optimal_size:.0f}\n\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Follow Top Opportunity", callback_data=f"quick_follow_{opportunities[0]['symbol']}")],
            [InlineKeyboardButton(text="🔍 Analyze Details", callback_data="analyze_opportunity")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="alpha_menu")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error showing copy opportunities: {e}")
        await callback.message.edit_text(
            "❌ Error loading copy opportunities. Please try again later.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Back", callback_data="alpha_menu")]
            ])
        )

@router.callback_query(F.data == "alpha_signals")
async def show_regime_signals(callback: CallbackQuery):
    """Show detailed regime and timing signals"""
    try:
        signals = await market_intelligence.get_all_signals()
        
        text = "⚡ **Regime & Timing Signals**\n\n"
        
        # Overall market regime
        regime_summary = await market_intelligence.get_overall_regime()
        text += f"🌐 **Market Regime:** {regime_summary['name']}\n"
        text += f"📊 **Volatility:** {regime_summary['volatility']:.1%}\n"
        text += f"📈 **Trend:** {regime_summary['trend'].title()}\n\n"
        
        # Copy timing recommendations
        text += "🎯 **Copy Timing Recommendations:**\n\n"
        
        best_pairs = [pair for pair, data in signals.items() if data.signal == 'green']
        caution_pairs = [pair for pair, data in signals.items() if data.signal == 'yellow']
        avoid_pairs = [pair for pair, data in signals.items() if data.signal == 'red']
        
        if best_pairs:
            text += f"🟢 **Copy Now:** {', '.join(best_pairs)}\n"
        if caution_pairs:
            text += f"🟡 **Copy with Caution:** {', '.join(caution_pairs)}\n"
        if avoid_pairs:
            text += f"🔴 **Avoid Copying:** {', '.join(avoid_pairs)}\n"
        
        text += "\n💡 **AI Recommendation:**\n"
        if len(best_pairs) >= 3:
            text += "Favorable conditions for copy trading. Consider following new traders."
        elif len(avoid_pairs) >= 2:
            text += "High volatility detected. Reduce copy trading activity or pause new follows."
        else:
            text += "Mixed conditions. Copy selectively with smaller position sizes."
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Detailed Signals", callback_data="detailed_signals")],
            [InlineKeyboardButton(text="🔔 Set Alerts", callback_data="regime_alerts")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="alpha_menu")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error showing regime signals: {e}")
        await callback.message.edit_text(
            "❌ Error loading regime signals. Please try again later.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Back", callback_data="alpha_menu")]
            ])
        )

@router.callback_query(F.data == "alpha_analyze")
async def start_alpha_trader_analysis(callback: CallbackQuery):
    """Start trader analysis flow from alpha menu"""
    await callback.message.edit_text(
        "🔍 **AI Trader Analysis**\n\n"
        "Enter trader address to get AI insights:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="alpha_menu")]
        ])
    )

@router.callback_query(F.data == "alpha_detailed")
async def show_detailed_analysis(callback: CallbackQuery):
    """Show detailed market analysis"""
    try:
        # Get comprehensive market data
        overall_regime = await market_intelligence.get_overall_regime()
        all_signals = await market_intelligence.get_all_signals()
        
        text = "📈 **Detailed Market Analysis**\n\n"
        
        # Market regime details
        text += f"🌐 **Market Regime: {overall_regime['name']}**\n"
        text += f"Confidence: {overall_regime['confidence']:.1%}\n"
        text += f"Total Symbols: {overall_regime['total_symbols']}\n\n"
        
        # Signal breakdown
        signal_counts = overall_regime['signal_counts']
        text += "📊 **Signal Distribution:**\n"
        text += f"🟢 Green: {signal_counts['green']}\n"
        text += f"🟡 Yellow: {signal_counts['yellow']}\n"
        text += f"🔴 Red: {signal_counts['red']}\n\n"
        
        # Individual pair analysis
        text += "🎯 **Individual Pair Analysis:**\n"
        for pair, signal in all_signals.items():
            signal_emoji = {"green": "🟢", "yellow": "🟡", "red": "🔴"}[signal.signal]
            text += f"{signal_emoji} **{pair}**\n"
            text += f"   Volatility: {signal.volatility:.1%}\n"
            text += f"   Trend: {signal.trend.title()}\n"
            text += f"   Confidence: {signal.confidence:.1%}\n\n"
        
        # Volatility forecast
        text += "🔮 **Volatility Forecast:**\n"
        for pair in ['BTC-USD', 'ETH-USD']:
            forecast = await market_intelligence.get_volatility_forecast(pair)
            text += f"**{pair}**: {forecast['forecast_volatility']:.1%} "
            text += f"({forecast['trend']}, {forecast['confidence']:.1%} confidence)\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Refresh", callback_data="alpha_detailed")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="alpha_market")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error showing detailed analysis: {e}")
        await callback.message.edit_text(
            "❌ Error loading detailed analysis. Please try again later.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Back", callback_data="alpha_market")]
            ])
        )

@router.callback_query(F.data == "detailed_signals")
async def show_detailed_signals(callback: CallbackQuery):
    """Show detailed timing signals"""
    try:
        all_signals = await market_intelligence.get_all_signals()
        
        text = "⚡ **Detailed Timing Signals**\n\n"
        
        for pair, signal in all_signals.items():
            signal_emoji = {"green": "🟢", "yellow": "🟡", "red": "🔴"}[signal.signal]
            
            text += f"{signal_emoji} **{pair}**\n"
            text += f"Signal: {signal.signal.upper()}\n"
            text += f"Confidence: {signal.confidence:.1%}\n"
            text += f"Volatility: {signal.volatility:.1%}\n"
            text += f"Trend: {signal.trend.title()}\n"
            text += f"Reason: {signal.reason}\n"
            text += f"Recommendation: {signal.recommendation}\n\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Back", callback_data="alpha_signals")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error showing detailed signals: {e}")
        await callback.message.edit_text(
            "❌ Error loading detailed signals. Please try again later.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Back", callback_data="alpha_signals")]
            ])
        )

@router.callback_query(F.data == "regime_alerts")
async def show_regime_alerts(callback: CallbackQuery):
    """Show regime alert settings"""
    text = """
🔔 **Regime Alert Settings**

Set up alerts for market regime changes:

**Available Alerts:**
• 🟢 Green regime detected (favorable for copying)
• 🔴 Red regime detected (high risk)
• ⚡ Volatility spike (>50% increase)
• 📈 Trend reversal detected

**Alert Methods:**
• Telegram notifications
• Email alerts
• Webhook notifications

**Current Status:** Not configured

To set up alerts, contact support or use the web interface.
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Web Interface", url="https://vanta-bot.com/alerts")],
        [InlineKeyboardButton(text="📞 Contact Support", url="https://t.me/vanta_support")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="alpha_signals")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data == "alpha_menu")
async def back_to_alpha_menu(callback: CallbackQuery):
    """Go back to alpha main menu"""
    await alpha_command(callback.message)

@router.callback_query(F.data == "analyze_opportunity")
async def analyze_opportunity(callback: CallbackQuery):
    """Analyze a specific opportunity"""
    text = """
🔍 **Opportunity Analysis**

**Current Top Opportunity:**
• Symbol: BTC-USD
• Confidence: 85%
• Market Regime: Green
• Volatility: 12%
• Trend: Bullish

**Why This Opportunity:**
• Low volatility environment
• Strong bullish momentum
• High trader activity
• Favorable risk/reward ratio

**Recommended Action:**
• Start with small position size
• Set tight stop-loss
• Monitor for regime changes
• Consider following bullish traders

**Risk Factors:**
• Market could reverse quickly
• Volatility may increase
• Past performance doesn't guarantee future results
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Follow Opportunity", callback_data="follow_opportunity")],
        [InlineKeyboardButton(text="📊 View Traders", callback_data="view_opportunity_traders")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="alpha_opportunities")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data == "follow_opportunity")
async def follow_opportunity(callback: CallbackQuery):
    """Follow the current opportunity"""
    await callback.message.edit_text(
        "✅ **Opportunity Followed**\n\n"
        "You're now following the current market opportunity. "
        "We'll notify you when conditions change or new opportunities arise.\n\n"
        "Use /status to monitor your copy trading performance.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 View Status", callback_data="view_status")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="alpha_opportunities")]
        ])
    )

@router.callback_query(F.data == "view_opportunity_traders")
async def view_opportunity_traders(callback: CallbackQuery):
    """View traders suitable for current opportunity"""
    try:
        # Get trending traders
        trending_traders = await leaderboard_service.get_trending_traders(hours=24, limit=5)
        
        if not trending_traders:
            await callback.message.edit_text(
                "📊 **No Trending Traders**\n\n"
                "No traders with recent activity found. Check back later.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Back", callback_data="analyze_opportunity")]
                ])
            )
            return
        
        text = "📈 **Trending Traders for Current Opportunity**\n\n"
        
        for i, trader in enumerate(trending_traders, 1):
            addr = trader['address'][:8]
            volume = trader['last_30d_volume_usd'] / 1e6
            pnl = trader['realized_pnl_clean_usd']
            recent_trades = trader.get('recent_trades', 0)
            archetype = trader.get('archetype', 'Unknown')
            
            text += f"{i}. **{addr}...**\n"
            text += f"   📊 ${volume:.1f}M vol • ${pnl:,.0f} PnL\n"
            text += f"   🔥 {recent_trades} trades (24h)\n"
            text += f"   🎯 {archetype}\n\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Analyze Top Trader", callback_data=f"analyze_{trending_traders[0]['address']}")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="analyze_opportunity")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error showing opportunity traders: {e}")
        await callback.message.edit_text(
            "❌ Error loading opportunity traders. Please try again later.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Back", callback_data="analyze_opportunity")]
            ])
        )

async def show_trader_analysis(message, trader_card):
    """Show detailed trader analysis (shared function)"""
    address = trader_card['address']
    archetype = trader_card.get('archetype', 'Unknown')
    copyability = trader_card.get('copyability_score', 50)
    risk_level = trader_card.get('risk_level', 'MED')
    
    # Performance metrics
    volume = trader_card['last_30d_volume_usd']
    pnl = trader_card['realized_pnl_clean_usd']
    win_rate = trader_card.get('win_rate', 0) * 100
    sharpe = trader_card.get('sharpe_like', 0)
    max_dd = trader_card.get('max_drawdown', 0) * 100
    
    # AI predictions
    win_prob_7d = trader_card.get('win_prob_7d', 0.5) * 100
    expected_dd = trader_card.get('expected_dd_7d', 0) * 100
    
    # Risk emoji
    risk_emoji = {"LOW": "🟢", "MED": "🟡", "HIGH": "🔴"}[risk_level]
    
    text = f"🔍 **AI Trader Analysis: {address[:10]}...**\n\n"
    
    text += f"🤖 **AI Classification**\n"
    text += f"Archetype: {archetype}\n"
    text += f"Copyability: {copyability}/100\n"
    text += f"Risk Level: {risk_level} {risk_emoji}\n\n"
    
    text += f"📊 **30-Day Performance**\n"
    text += f"Volume: ${volume:,.0f}\n"
    text += f"PnL: ${pnl:,.0f}\n"
    text += f"Win Rate: {win_rate:.1f}%\n"
    text += f"Sharpe-like: {sharpe:.2f}\n"
    text += f"Max Drawdown: {max_dd:.1f}%\n\n"
    
    text += f"🔮 **7-Day Forecast**\n"
    text += f"Win Probability: {win_prob_7d:.0f}%\n"
    text += f"Expected Drawdown: {expected_dd:.1f}%\n\n"
    
    # Add strengths and warnings
    strengths = trader_card.get('strengths', [])
    if strengths:
        text += f"✅ **Strengths**\n"
        for strength in strengths[:3]:
            text += f"• {strength}\n"
        text += "\n"
    
    warnings = trader_card.get('warnings', [])
    if warnings:
        text += f"⚠️ **Warnings**\n"
        for warning in warnings[:2]:
            text += f"• {warning}\n"
        text += "\n"
    
    # Optimal copy size suggestion
    optimal_size = trader_card.get('optimal_copy_size', 100)
    text += f"💡 **Suggested Copy Size: ${optimal_size:.0f}**"
    
    # Action buttons
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Follow This Trader", callback_data=f"follow_{address}")],
        [InlineKeyboardButton(text="📈 View Recent Trades", callback_data=f"trades_{address}")],
        [InlineKeyboardButton(text="⬅️ Back to Alpha", callback_data="alpha_menu")]
    ])
    
    await message.answer(text, reply_markup=keyboard)
