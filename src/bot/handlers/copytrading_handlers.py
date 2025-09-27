"""
Copy Trading Handlers for Vanta Bot
Telegram bot handlers for copy trading functionality
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from ...copy_trading.copy_executor import CopyExecutor
from ...copy_trading.leaderboard_service import LeaderboardService

logger = logging.getLogger(__name__)

class CopyTradingStates(StatesGroup):
    creating_copytrader = State()
    configuring_sizing = State()
    configuring_risk = State()
    selecting_leader = State()

router = Router()

# Global instances (would be injected in real implementation)
copy_executor: Optional[CopyExecutor] = None
leaderboard_service: Optional[LeaderboardService] = None

def set_services(executor: CopyExecutor, leaderboard: LeaderboardService):
    """Set the service instances"""
    global copy_executor, leaderboard_service
    copy_executor = executor
    leaderboard_service = leaderboard

@router.message(Command("copytrader"))
async def copytrader_command(message: Message, state: FSMContext):
    """Main copytrader management command"""
    user_id = message.from_user.id
    
    # Get existing copytraders
    copytraders = await copy_executor.get_copy_status(user_id)
    
    if not copytraders['profiles']:
        # First time setup
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤖 Create New Copytrader", callback_data="create_copytrader")],
            [InlineKeyboardButton(text="📊 View Top Traders", callback_data="view_leaderboard")],
            [InlineKeyboardButton(text="❓ Help", callback_data="copytrader_help")]
        ])
        
        await message.answer(
            "🤖 **Welcome to AI Copy Trading!**\n\n"
            "Copy trades from the best Avantis traders automatically. "
            "Get started by creating your first Copytrader profile.",
            reply_markup=keyboard
        )
    else:
        # Show existing copytraders
        await show_copytrader_dashboard(message, copytraders)

@router.callback_query(F.data == "create_copytrader")
async def create_copytrader_start(callback: CallbackQuery, state: FSMContext):
    """Start copytrader creation flow"""
    await callback.message.edit_text(
        "🤖 **Create New Copytrader**\n\n"
        "Choose a name for your copytrader profile:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_creation")]
        ])
    )
    await state.set_state(CopyTradingStates.creating_copytrader)

@router.message(CopyTradingStates.creating_copytrader)
async def handle_copytrader_name(message: Message, state: FSMContext):
    """Handle copytrader name input"""
    name = message.text.strip()
    
    if len(name) < 3 or len(name) > 50:
        await message.answer("❌ Name must be between 3-50 characters. Try again:")
        return
    
    await state.update_data(name=name)
    
    # Show sizing configuration
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Fixed Amount ($)", callback_data="sizing_fixed")],
        [InlineKeyboardButton(text="📊 Percentage (%)", callback_data="sizing_percent")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_creation")]
    ])
    
    await message.answer(
        f"✅ Copytrader name: **{name}**\n\n"
        "🎯 **Choose Copy Sizing Method:**\n\n"
        "💰 **Fixed Amount**: Copy with same dollar amount each time\n"
        "📊 **Percentage**: Copy with % of your total balance",
        reply_markup=keyboard
    )
    await state.set_state(CopyTradingStates.configuring_sizing)

@router.callback_query(F.data.startswith("sizing_"))
async def handle_sizing_method(callback: CallbackQuery, state: FSMContext):
    """Handle sizing method selection"""
    method = callback.data.split("_")[1]  # "fixed" or "percent"
    await state.update_data(sizing_mode=method)
    
    if method == "fixed":
        prompt = "💰 Enter fixed amount in USD (e.g., 100):"
        example = "Example: 100 (will copy $100 worth of each trade)"
    else:
        prompt = "📊 Enter percentage (1-20%):"
        example = "Example: 5 (will copy 5% of your balance for each trade)"
    
    await callback.message.edit_text(
        f"🎯 **Sizing Configuration**\n\n{prompt}\n\n_{example}_",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_creation")]
        ])
    )

@router.message(Command("alfa"))
async def alfa_leaderboard(message: Message):
    """Show AI-powered trader leaderboard"""
    # Get top traders
    top_traders = await leaderboard_service.get_top_traders(limit=10)
    
    if not top_traders:
        await message.answer("📊 No trader data available yet. Check back soon!")
        return
    
    # Format leaderboard
    text = "🏆 **Top AI-Ranked Traders**\n\n"
    
    for i, trader in enumerate(top_traders, 1):
        copyability = trader.get('copyability_score', 50)
        volume = trader['last_30d_volume_usd']
        pnl = trader['realized_pnl_clean_usd']
        archetype = trader.get('archetype', 'Unknown')
        
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        
        text += (
            f"{emoji} **{trader['address'][:8]}...** "
            f"({copyability}/100)\n"
            f"   🎯 {archetype}\n"
            f"   💰 ${volume:,.0f} • PnL: ${pnl:,.0f}\n\n"
        )
    
    # Add action buttons
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Full Leaderboard", callback_data="full_leaderboard")],
        [InlineKeyboardButton(text="🔍 Analyze Trader", callback_data="analyze_trader")],
        [InlineKeyboardButton(text="📊 Market Signals", callback_data="market_signals")]
    ])
    
    await message.answer(text, reply_markup=keyboard)

@router.callback_query(F.data == "full_leaderboard")
async def show_full_leaderboard(callback: CallbackQuery):
    """Show paginated full leaderboard"""
    top_traders = await leaderboard_service.get_top_traders(limit=50)
    
    # Create pagination
    page = 0
    page_size = 10
    total_pages = (len(top_traders) + page_size - 1) // page_size
    
    await show_leaderboard_page(callback.message, top_traders, page, total_pages)

async def show_leaderboard_page(message, traders, page, total_pages):
    """Show a specific page of the leaderboard"""
    page_size = 10
    start_idx = page * page_size
    end_idx = min(start_idx + page_size, len(traders))
    page_traders = traders[start_idx:end_idx]
    
    text = f"🏆 **Top Traders** (Page {page + 1}/{total_pages})\n\n"
    
    for i, trader in enumerate(page_traders, start_idx + 1):
        copyability = trader.get('copyability_score', 50)
        volume = trader['last_30d_volume_usd'] / 1e6  # Convert to millions
        pnl_pct = (trader['realized_pnl_clean_usd'] / max(trader['last_30d_volume_usd'], 1)) * 100
        risk = trader.get('risk_level', 'MED')
        
        risk_emoji = {"LOW": "🟢", "MED": "🟡", "HIGH": "🔴"}[risk]
        
        text += (
            f"{i}. **{trader['address'][:10]}...** "
            f"({copyability}/100) {risk_emoji}\n"
            f"   📊 ${volume:.1f}M vol • {pnl_pct:+.1f}% return\n"
            f"   🎯 {trader.get('archetype', 'Unknown')}\n\n"
        )
    
    # Pagination buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Previous", callback_data=f"page_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"page_{page+1}"))
    
    action_buttons = [
        [InlineKeyboardButton(text="🔍 Analyze Trader", callback_data="analyze_trader")],
        [InlineKeyboardButton(text="➕ Follow Trader", callback_data="follow_trader")]
    ]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        nav_buttons,
        *action_buttons
    ])
    
    if message.text:
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)

@router.callback_query(F.data == "analyze_trader")
async def start_trader_analysis(callback: CallbackQuery, state: FSMContext):
    """Start trader analysis flow"""
    await callback.message.edit_text(
        "🔍 **Trader Analysis**\n\n"
        "Enter trader address to get AI insights:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="back_to_leaderboard")]
        ])
    )
    await state.set_state(CopyTradingStates.selecting_leader)

@router.message(CopyTradingStates.selecting_leader)
async def handle_trader_analysis_request(message: Message, state: FSMContext):
    """Handle trader address for analysis"""
    address = message.text.strip()
    
    # Validate address format
    if not address.startswith('0x') or len(address) != 42:
        await message.answer("❌ Invalid address format. Please enter a valid Ethereum address:")
        return
    
    await state.clear()
    
    # Get trader analysis
    trader_card = await leaderboard_service.get_trader_card(address)
    
    if not trader_card:
        await message.answer(f"❌ No data found for trader {address[:10]}...")
        return
    
    # Format analysis
    await show_trader_analysis(message, trader_card)

async def show_trader_analysis(message, trader_card):
    """Show detailed trader analysis"""
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
    
    text = f"🔍 **Trader Analysis: {address[:10]}...**\n\n"
    
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
        [InlineKeyboardButton(text="⬅️ Back to Leaderboard", callback_data="back_to_leaderboard")]
    ])
    
    await message.answer(text, reply_markup=keyboard)

@router.message(Command("status"))
async def copy_status_command(message: Message):
    """Show copy trading status"""
    user_id = message.from_user.id
    status = await copy_executor.get_copy_status(user_id)
    
    if not status['profiles']:
        await message.answer(
            "🤖 You haven't created any copytraders yet.\n\n"
            "Use /copytrader to get started with AI copy trading!"
        )
        return
    
    # Format status
    text = "📊 **Copy Trading Status**\n\n"
    
    # Performance overview
    perf = status['performance']
    total_pnl = perf['total_pnl']
    copy_attribution = perf['copy_attribution'] * 100
    
    text += f"💰 **Total PnL: ${total_pnl:,.2f}**\n"
    text += f"Manual: ${perf['manual_pnl']:,.2f}\n"
    text += f"Copy: ${perf['copy_pnl']:,.2f} ({copy_attribution:.1f}%)\n\n"
    
    # Active follows
    if status['following']:
        text += f"👥 **Following {len(status['following'])} Traders:**\n"
        for follow in status['following'][:5]:
            addr = follow['leader_address'][:8]
            days_following = (datetime.utcnow() - follow['started_at']).days
            pnl = follow.get('realized_pnl_clean_usd', 0)
            text += f"• {addr}... ({days_following}d) - ${pnl:,.0f} PnL\n"
        
        if len(status['following']) > 5:
            text += f"• ... and {len(status['following']) - 5} more\n"
        text += "\n"
    
    # Recent positions
    if status['recent_positions']:
        text += f"📋 **Recent Copy Trades:**\n"
        for pos in status['recent_positions'][:3]:
            addr = pos['leader_address'][:8]
            status_emoji = {"OPEN": "🟢", "CLOSED": "✅", "FAILED": "❌"}[pos['status']]
            pnl_text = f"${pos.get('pnl_usd', 0):,.0f}" if pos.get('pnl_usd') else "Pending"
            text += f"{status_emoji} {addr}... - {pnl_text}\n"
    
    # Action buttons
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Manage Copytraders", callback_data="manage_copytraders")],
        [InlineKeyboardButton(text="📊 Full Performance", callback_data="full_performance")],
        [InlineKeyboardButton(text="🔄 Refresh", callback_data="refresh_status")]
    ])
    
    await message.answer(text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("follow_"))
async def follow_trader_callback(callback: CallbackQuery):
    """Handle follow trader callback"""
    address = callback.data.split("_", 1)[1]
    
    # Get user ID
    user_id = callback.from_user.id
    
    # Create default configuration
    config = {
        'name': f'Copytrader_{address[:8]}',
        'sizing_mode': 'FIXED_NOTIONAL',
        'sizing_value': 100,
        'max_slippage_bps': 100,
        'max_leverage': 50,
        'notional_cap': 1000,
        'pair_filters': {},
        'tp_sl_policy': {}
    }
    
    # Start following
    result = await copy_executor.follow_trader(user_id, address, config)
    
    if result['success']:
        await callback.message.edit_text(
            f"✅ **Successfully started following {address[:10]}...**\n\n"
            f"Your copytrader will now automatically copy trades according to your settings.\n\n"
            f"Use /status to monitor your copy trading performance.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📊 View Status", callback_data="view_status")],
                [InlineKeyboardButton(text="⬅️ Back to Analysis", callback_data=f"analyze_{address}")]
            ])
        )
    else:
        await callback.message.edit_text(
            f"❌ **Failed to follow trader**\n\n"
            f"Error: {result['error']}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Back", callback_data="back_to_leaderboard")]
            ])
        )

@router.callback_query(F.data == "copytrader_help")
async def copytrader_help(callback: CallbackQuery):
    """Show copy trading help"""
    help_text = """
🤖 **AI Copy Trading Help**

**What is Copy Trading?**
Copy trading allows you to automatically replicate trades from successful traders on Avantis Protocol.

**How it Works:**
1. 🏆 Browse top traders using /alfa
2. 🔍 Analyze trader performance and risk
3. ➕ Follow traders you want to copy
4. ⚙️ Configure copy settings (size, risk limits)
5. 🚀 Trades are copied automatically

**Commands:**
• `/copytrader` - Manage your copytraders
• `/alfa` - View AI-ranked trader leaderboard
• `/status` - Check copy trading performance
• `/alpha` - Get market intelligence

**Risk Management:**
• Set position size limits
• Configure maximum leverage
• Use pair filters to avoid certain assets
• Monitor performance regularly

**Tips:**
• Start with small position sizes
• Follow multiple traders for diversification
• Monitor market conditions using /alpha
• Review and adjust settings regularly
"""
    
    await callback.message.edit_text(
        help_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Back", callback_data="back_to_copytrader")]
        ])
    )

@router.callback_query(F.data == "cancel_creation")
async def cancel_creation(callback: CallbackQuery, state: FSMContext):
    """Cancel copytrader creation"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Copytrader creation cancelled.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Try Again", callback_data="create_copytrader")]
        ])
    )

@router.callback_query(F.data == "back_to_leaderboard")
async def back_to_leaderboard(callback: CallbackQuery):
    """Go back to leaderboard"""
    await alfa_leaderboard(callback.message)

@router.callback_query(F.data == "back_to_copytrader")
async def back_to_copytrader(callback: CallbackQuery):
    """Go back to copytrader main menu"""
    await copytrader_command(callback.message, None)

async def show_copytrader_dashboard(message, copytraders):
    """Show copytrader dashboard for existing users"""
    text = "🤖 **Your Copytraders**\n\n"
    
    for profile in copytraders['profiles']:
        text += f"📊 **{profile['name']}**\n"
        text += f"Status: {'🟢 Active' if profile['is_enabled'] else '🔴 Inactive'}\n"
        text += f"Sizing: {profile['sizing_mode']} - {profile['sizing_value']}\n\n"
    
    # Performance summary
    perf = copytraders['performance']
    text += f"💰 **Performance Summary**\n"
    text += f"Total PnL: ${perf['total_pnl']:,.2f}\n"
    text += f"Copy Attribution: {perf['copy_attribution']*100:.1f}%\n\n"
    
    # Action buttons
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Create New", callback_data="create_copytrader")],
        [InlineKeyboardButton(text="📊 View Leaderboard", callback_data="view_leaderboard")],
        [InlineKeyboardButton(text="⚙️ Manage", callback_data="manage_copytraders")]
    ])
    
    await message.answer(text, reply_markup=keyboard)
