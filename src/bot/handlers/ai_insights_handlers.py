"""
AI Insights Handlers for Vanta Bot
Telegram bot handlers for AI insights and market intelligence
"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:  # pragma: no cover
    from src.services.analytics.insights_service import InsightsService

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# Global service injected at application start
insights_service: Optional["InsightsService"] = None


def set_insights_service(service) -> None:
    """Inject the insights service used by handlers."""
    global insights_service
    insights_service = service

async def alpha_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """AI insights and market intelligence command"""
    text = (
        "🤖 **AI Insights & Market Intelligence**\n\n"
        "Choose an option:"
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=get_ai_insights_keyboard(),
        )
    else:
        await update.effective_message.reply_text(
            text,
            parse_mode='Markdown',
            reply_markup=get_ai_insights_keyboard(),
        )

async def alfa_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display AI-ranked leaderboard"""
    try:
        if not insights_service:
            await update.callback_query.edit_message_text(
                "⚠️ Insights service not available",
                reply_markup=get_back_keyboard()
            )
            return

        top_traders = await insights_service.get_leaderboard(limit=10)
        
        if not top_traders:
            await update.callback_query.edit_message_text(
                "📊 **AI Leaderboard**\n\n"
                "No traders available at the moment.",
                parse_mode='Markdown',
                reply_markup=get_back_keyboard()
            )
            return
        
        # Format leaderboard
        leaderboard_text = "🏆 **Top AI-Ranked Traders**\n\n"
        
        for i, trader in enumerate(top_traders[:10], 1):
            address = trader.get('address', 'Unknown')
            score = trader.get('copyability_score', 0)
            volume = trader.get('notional', 0)
            pnl = trader.get('total_pnl', 0)
            archetype = trader.get('archetype', 'Unknown')
            risk_level = trader.get('risk_level', 'MED')
            
            leaderboard_text += f"{i}. **{address}**\n"
            leaderboard_text += f"   Score: {score}/100 | {archetype}\n"
            leaderboard_text += f"   Volume: ${volume:,.0f} | PnL: ${pnl:,.0f}\n"
            leaderboard_text += f"   Risk: {risk_level}\n\n"
        
        await update.callback_query.edit_message_text(
            leaderboard_text,
            parse_mode='Markdown',
            reply_markup=get_leaderboard_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in alfa_leaderboard: {e}")
        await update.callback_query.edit_message_text(
            "❌ Error loading leaderboard. Please try again.",
            reply_markup=get_back_keyboard()
        )

async def ai_market_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display AI market signal"""
    try:
        if not insights_service:
            await update.callback_query.edit_message_text(
                "⚠️ Market intelligence service not available",
                reply_markup=get_back_keyboard()
            )
            return
        
        signal = await insights_service.get_market_signal()
        
        if not signal:
            await update.callback_query.edit_message_text(
                "📊 **AI Market Signal**\n\n"
                "No signal available at the moment.",
                parse_mode='Markdown',
                reply_markup=get_back_keyboard()
            )
            return
        
        signal_text = "📊 **AI Market Signal**\n\n"
        signal_text += f"**Signal:** {signal.get('signal', 'Unknown').title()}\n"
        signal_text += f"**Confidence:** {signal.get('confidence', 0):.0%}\n"
        signal_text += f"**Timeframe:** {signal.get('timeframe', 'Unknown')}\n"
        signal_text += f"**Updated:** {signal.get('updated_at', 'Unknown')}\n\n"

        if signal.get('reasoning'):
            signal_text += f"**Reasoning:** {signal['reasoning']}\n\n"
        
        await update.callback_query.edit_message_text(
            signal_text,
            parse_mode='Markdown',
            reply_markup=get_back_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in ai_market_signal: {e}")
        await update.callback_query.edit_message_text(
            "❌ Error loading market signal. Please try again.",
            reply_markup=get_back_keyboard()
        )

async def copy_opportunities(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display copy trading opportunities"""
    try:
        if not insights_service:
            await update.callback_query.edit_message_text(
                "⚠️ Market intelligence service not available",
                reply_markup=get_back_keyboard()
            )
            return
        
        opportunities = await insights_service.get_copy_opportunities()
        
        if not opportunities:
            await update.callback_query.edit_message_text(
                "🎯 **Copy Opportunities**\n\n"
                "No opportunities found at the moment.",
                parse_mode='Markdown',
                reply_markup=get_back_keyboard()
            )
            return
        
        opportunities_text = "🎯 **Copy Opportunities**\n\n"
        
        for opp in opportunities[:5]:  # Show top 5
            trader = opp.get('trader', {})
            address = trader.get('address', 'Unknown')
            score = opp.get('opportunity_score', 0)
            reason = opp.get('reason', 'Good opportunity')
            
            opportunities_text += f"**{address}**\n"
            opportunities_text += f"Score: {score}/100\n"
            opportunities_text += f"Reason: {reason}\n\n"
        
        await update.callback_query.edit_message_text(
            opportunities_text,
            parse_mode='Markdown',
            reply_markup=get_back_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in copy_opportunities: {e}")
        await update.callback_query.edit_message_text(
            "❌ Error loading opportunities. Please try again.",
            reply_markup=get_back_keyboard()
        )

async def ai_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display AI dashboard"""
    try:
        if not insights_service:
            await update.callback_query.edit_message_text(
                "⚠️ Market intelligence service not available",
                reply_markup=get_back_keyboard()
            )
            return
        
        dashboard = await insights_service.get_dashboard()
        signals = dashboard.get('signals', [])
        
        dashboard_text = "🤖 **AI Trading Dashboard**\n\n"
        
        if dashboard:
            dashboard_text += f"**Market Regime:** {dashboard.get('regime', 'Unknown').title()}\n"
            dashboard_text += f"**Confidence:** {dashboard.get('confidence', 0):.0%}\n\n"

        if signals:
            dashboard_text += "**Active Signals:**\n"
            for signal in signals[:3]:
                dashboard_text += f"• {signal.get('symbol', 'Unknown')}: {signal.get('signal', 'Unknown').title()} ({signal.get('confidence', 0):.0%})\n"
            dashboard_text += "\n"
        
        await update.callback_query.edit_message_text(
            dashboard_text,
            parse_mode='Markdown',
            reply_markup=get_back_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in ai_dashboard: {e}")
        await update.callback_query.edit_message_text(
            "❌ Error loading dashboard. Please try again.",
            reply_markup=get_back_keyboard()
        )

async def market_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display market analysis"""
    try:
        if not insights_service:
            await update.callback_query.edit_message_text(
                "⚠️ Market intelligence service not available",
                reply_markup=get_back_keyboard()
            )
            return
        
        summary = await insights_service.get_market_analysis()
        
        if not summary:
            await update.callback_query.edit_message_text(
                "📊 **Market Analysis**\n\n"
                "No analysis available at the moment.",
                parse_mode='Markdown',
                reply_markup=get_back_keyboard()
            )
            return
        
        analysis_text = "📊 **Market Analysis**\n\n"
        analysis_text += f"**Overall Sentiment:** {summary.get('sentiment', 'Unknown').title()}\n"
        analysis_text += f"**Volatility:** {summary.get('volatility', 'Unknown')}\n"
        analysis_text += f"**Trend:** {summary.get('trend', 'Unknown')}\n\n"

        if summary.get('key_insights'):
            analysis_text += "**Key Insights:**\n"
            for insight in summary['key_insights'][:3]:
                analysis_text += f"• {insight}\n"
            analysis_text += "\n"
        
        await update.callback_query.edit_message_text(
            analysis_text,
            parse_mode='Markdown',
            reply_markup=get_back_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in market_analysis: {e}")
        await update.callback_query.edit_message_text(
            "❌ Error loading market analysis. Please try again.",
            reply_markup=get_back_keyboard()
        )

async def trader_analytics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display trader analytics"""
    try:
        if not insights_service:
            await update.callback_query.edit_message_text(
                "⚠️ Market intelligence service not available",
                reply_markup=get_back_keyboard()
            )
            return
        
        analytics = await insights_service.get_trader_analytics_summary()
        
        if not analytics:
            await update.callback_query.edit_message_text(
                "📈 **Trader Analytics**\n\n"
                "No analytics available at the moment.",
                parse_mode='Markdown',
                reply_markup=get_back_keyboard()
            )
            return
        
        analytics_text = "📈 **Trader Analytics**\n\n"
        analytics_text += f"**Total Traders:** {analytics.get('total_traders', 0)}\n"
        analytics_text += f"**Active Traders:** {analytics.get('active_traders', 0)}\n"
        analytics_text += f"**Avg Performance:** {analytics.get('avg_performance', 0):.1%}\n\n"

        if analytics.get('top_archetypes'):
            analytics_text += "**Top Archetypes:**\n"
            for archetype in analytics['top_archetypes'][:3]:
                analytics_text += f"• {archetype}\n"
        
        await update.callback_query.edit_message_text(
            analytics_text,
            parse_mode='Markdown',
            reply_markup=get_back_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in trader_analytics: {e}")
        await update.callback_query.edit_message_text(
            "❌ Error loading trader analytics. Please try again.",
            reply_markup=get_back_keyboard()
        )

def get_ai_insights_keyboard():
    """Get AI insights keyboard"""
    keyboard = [
        [InlineKeyboardButton("🏆 AI Leaderboard", callback_data="alfa_leaderboard")],
        [InlineKeyboardButton("📊 Market Signal", callback_data="ai_market_signal")],
        [InlineKeyboardButton("🎯 Copy Opportunities", callback_data="copy_opportunities")],
        [InlineKeyboardButton("🤖 AI Dashboard", callback_data="ai_dashboard")],
        [InlineKeyboardButton("📈 Market Analysis", callback_data="market_analysis")],
        [InlineKeyboardButton("📊 Trader Analytics", callback_data="trader_analytics")],
        [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_leaderboard_keyboard():
    """Get leaderboard keyboard"""
    keyboard = [
        [InlineKeyboardButton("🔄 Refresh", callback_data="alfa_leaderboard")],
        [InlineKeyboardButton("🔙 Back", callback_data="ai_insights")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_keyboard():
    """Get back keyboard"""
    keyboard = [
        [InlineKeyboardButton("🔙 Back", callback_data="ai_insights")]
    ]
    return InlineKeyboardMarkup(keyboard)
