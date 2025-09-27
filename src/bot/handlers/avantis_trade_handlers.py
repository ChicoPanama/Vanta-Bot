"""
Avantis Trade Handlers - Telegram Command Handlers

This module provides Telegram command handlers for Avantis trading operations
using the integrated Avantis Trader SDK with safety controls.
"""

import os
import logging
import re
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from src.integrations.avantis.sdk_client import get_sdk_client
from src.services.markets.avantis_price_provider import get_price_provider
from src.services.trading.avantis_executor import get_executor, OrderRequest, get_execution_mode, set_execution_mode
from src.services.trading.avantis_positions import get_positions_manager

logger = logging.getLogger(__name__)


async def a_price_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /a_price command - Get price information for a trading pair
    
    Usage: /a_price <PAIR>
    Example: /a_price ETH/USD
    """
    try:
        if not context.args:
            await update.message.reply_text(
                "❌ **Usage:** `/a_price <PAIR>`\n"
                "**Example:** `/a_price ETH/USD`",
                parse_mode='Markdown'
            )
            return
        
        pair = context.args[0].upper()
        
        # Validate pair format
        if not re.match(r'^[A-Z]+/[A-Z]+$', pair):
            await update.message.reply_text(
                "❌ **Invalid pair format.** Use format like: `ETH/USD`, `BTC/USD`",
                parse_mode='Markdown'
            )
            return
        
        # Get price provider
        price_provider = get_price_provider()
        
        # Get pair information
        pair_info = await price_provider.get_pair_info(pair)
        
        if not pair_info:
            await update.message.reply_text(
                f"❌ **Pair not found:** `{pair}`\n"
                f"Use `/a_pairs` to see available trading pairs.",
                parse_mode='Markdown'
            )
            return
        
        # Format response
        response = f"📊 **{pair} Price Information**\n\n"
        response += f"**Pair Index:** `{pair_info['pair_index']}`\n"
        
        if pair_info['pair_spread']:
            spread = pair_info['pair_spread']
            response += f"**Current Spread:** {spread.bid_price:.4f} / {spread.ask_price:.4f}\n"
        
        if pair_info['price_impact_long']:
            response += f"**Price Impact (Long):** {pair_info['price_impact_long']:.2f}%\n"
        
        if pair_info['price_impact_short']:
            response += f"**Price Impact (Short):** {pair_info['price_impact_short']:.2f}%\n"
        
        if pair_info['skew_impact_long']:
            response += f"**Skew Impact (Long):** {pair_info['skew_impact_long']:.2f}%\n"
        
        if pair_info['skew_impact_short']:
            response += f"**Skew Impact (Short):** {pair_info['skew_impact_short']:.2f}%\n"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"❌ Error in a_price_handler: {e}")
        await update.message.reply_text(
            "❌ **Error getting price information.** Please try again later.",
            parse_mode='Markdown'
        )


async def a_open_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /a_open command - Open a new position
    
    Usage: /a_open <PAIR> <long|short> <collateral_usdc> <leverage> [slippage_pct] [zero_fee]
    Example: /a_open ETH/USD long 25 20 1.0 false
    """
    try:
        if len(context.args) < 4:
            await update.message.reply_text(
                "❌ **Usage:** `/a_open <PAIR> <long|short> <collateral_usdc> <leverage> [slippage_pct] [zero_fee]`\n\n"
                "**Parameters:**\n"
                "• `PAIR`: Trading pair (e.g., ETH/USD)\n"
                "• `side`: long or short\n"
                "• `collateral_usdc`: Collateral amount in USDC\n"
                "• `leverage`: Leverage multiplier (1-100)\n"
                "• `slippage_pct`: Slippage percentage (optional, default: 1.0)\n"
                "• `zero_fee`: Use zero fee order (optional, default: false)\n\n"
                "**Example:** `/a_open ETH/USD long 25 20 1.0 false`",
                parse_mode='Markdown'
            )
            return
        
        # Parse arguments
        pair = context.args[0].upper()
        side = context.args[1].lower()
        collateral = float(context.args[2])
        leverage = float(context.args[3])
        slippage_pct = float(context.args[4]) if len(context.args) > 4 else 1.0
        zero_fee = context.args[5].lower() == 'true' if len(context.args) > 5 else False
        
        # Validate inputs
        if side not in ['long', 'short']:
            await update.message.reply_text(
                "❌ **Invalid side.** Use `long` or `short`.",
                parse_mode='Markdown'
            )
            return
        
        if collateral <= 0:
            await update.message.reply_text(
                "❌ **Invalid collateral.** Must be greater than 0.",
                parse_mode='Markdown'
            )
            return
        
        if leverage < 1 or leverage > 100:
            await update.message.reply_text(
                "❌ **Invalid leverage.** Must be between 1 and 100.",
                parse_mode='Markdown'
            )
            return
        
        # Validate pair format
        if not re.match(r'^[A-Z]+/[A-Z]+$', pair):
            await update.message.reply_text(
                "❌ **Invalid pair format.** Use format like: `ETH/USD`, `BTC/USD`",
                parse_mode='Markdown'
            )
            return
        
        # Get trader info
        sdk_client = get_sdk_client()
        client = sdk_client.get_client()
        trader_address = client.get_trader_address()
        
        if not trader_address:
            await update.message.reply_text(
                "❌ **No trader configured.** Please configure your private key or AWS KMS.",
                parse_mode='Markdown'
            )
            return
        
        # Get price provider and quote
        price_provider = get_price_provider()
        quote = await price_provider.quote_open(pair, side == 'long', collateral, leverage)
        
        # Create order request
        order = OrderRequest(
            pair=pair,
            is_long=(side == 'long'),
            collateral_usdc=collateral,
            leverage=leverage,
            order_type="market",
            slippage_pct=slippage_pct
        )
        
        # Execute trade
        executor = get_executor()
        result = await executor.open_market(order, zero_fee)
        
        if result.success:
            # Add execution mode warning
            execution_mode = get_execution_mode()
            mode_prefix = "⚠️" if execution_mode == "LIVE" else "🔍"
            
            response = f"{mode_prefix} **Position {'Executed' if execution_mode == 'LIVE' else 'Simulated'}**\n\n"
            response += f"**Pair:** `{pair}`\n"
            response += f"**Side:** `{side.upper()}`\n"
            response += f"**Collateral:** `{collateral} USDC`\n"
            response += f"**Leverage:** `{leverage}x`\n"
            response += f"**Position Size:** `{quote['position_size']:.2f} USDC`\n"
            response += f"**Opening Fee:** `{quote['opening_fee_usdc']:.4f} USDC`\n"
            response += f"**Loss Protection:** `{quote['loss_protection_percent']:.2f}%`\n"
            response += f"**Slippage:** `{slippage_pct}%`\n"
            response += f"**Zero Fee:** `{zero_fee}`\n\n"
            response += f"**Transaction:** `{result.tx_hash}`\n"
            response += f"**Trader:** `{trader_address[:10]}...`\n"
            response += f"**Mode:** `{execution_mode}`"
            
            await update.message.reply_text(response, parse_mode='Markdown')
        else:
            await update.message.reply_text(
                f"❌ **Failed to open position:** {result.error}",
                parse_mode='Markdown'
            )
        
    except ValueError as e:
        await update.message.reply_text(
            "❌ **Invalid number format.** Please check your input values.",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"❌ Error in a_open_handler: {e}")
        await update.message.reply_text(
            "❌ **Error opening position.** Please try again later.",
            parse_mode='Markdown'
        )


async def a_trades_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /a_trades command - List open trades
    """
    try:
        # Get trader info
        sdk_client = get_sdk_client()
        client = sdk_client.get_client()
        trader_address = client.get_trader_address()
        
        if not trader_address:
            await update.message.reply_text(
                "❌ **No trader configured.** Please configure your private key or AWS KMS.",
                parse_mode='Markdown'
            )
            return
        
        # Get positions
        positions_manager = get_positions_manager()
        trades, pending_orders = await positions_manager.get_trades(trader_address)
        
        if not trades and not pending_orders:
            await update.message.reply_text(
                "📊 **No Open Positions**\n\nYou don't have any open trades or pending orders.",
                parse_mode='Markdown'
            )
            return
        
        # Format response
        response = f"📊 **Open Positions & Orders**\n\n"
        response += f"**Trader:** `{trader_address[:10]}...`\n\n"
        
        if trades:
            response += f"**Active Trades:** {len(trades)}\n"
            for i, trade in enumerate(trades[:5], 1):  # Show max 5 trades
                try:
                    summary = await positions_manager.get_position_summary(trade)
                    direction = "🟢 LONG" if summary.is_long else "🔴 SHORT"
                    pnl_emoji = "💰" if summary.pnl >= 0 else "📉"
                    
                    response += f"\n**{i}.** {summary.pair} {direction}\n"
                    response += f"   Size: `{summary.size:.2f} USDC` @ `{summary.leverage}x`\n"
                    response += f"   Entry: `{summary.entry_price:.4f}`\n"
                    response += f"   PnL: {pnl_emoji} `{summary.pnl:.2f} USDC` (`{summary.pnl_percent:.2f}%`)\n"
                    response += f"   Index: `{summary.trade_index}`\n"
                except Exception as e:
                    logger.warning(f"Could not format trade {i}: {e}")
                    continue
            
            if len(trades) > 5:
                response += f"\n... and {len(trades) - 5} more trades"
        
        if pending_orders:
            response += f"\n\n**Pending Orders:** {len(pending_orders)}\n"
            for i, order in enumerate(pending_orders[:3], 1):  # Show max 3 pending orders
                response += f"**{i}.** Pair {order.pair_index} - Limit Order\n"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"❌ Error in a_trades_handler: {e}")
        await update.message.reply_text(
            "❌ **Error getting trades.** Please try again later.",
            parse_mode='Markdown'
        )


async def a_close_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /a_close command - Close a position
    
    Usage: /a_close <pair_index> <trade_index> [fraction]
    Example: /a_close 1 0 1.0 (close full position)
    Example: /a_close 1 0 0.5 (close 50% of position)
    """
    try:
        if len(context.args) < 2:
            await update.message.reply_text(
                "❌ **Usage:** `/a_close <pair_index> <trade_index> [fraction]`\n\n"
                "**Parameters:**\n"
                "• `pair_index`: Trading pair index\n"
                "• `trade_index`: Trade index to close\n"
                "• `fraction`: Fraction to close (0.0-1.0, default: 1.0 = full close)\n\n"
                "**Examples:**\n"
                "• `/a_close 1 0` - Close full position\n"
                "• `/a_close 1 0 0.5` - Close 50% of position\n\n"
                "Use `/a_trades` to see your open positions and their indices.",
                parse_mode='Markdown'
            )
            return
        
        # Parse arguments
        pair_index = int(context.args[0])
        trade_index = int(context.args[1])
        fraction = float(context.args[2]) if len(context.args) > 2 else 1.0
        
        # Validate inputs
        if fraction <= 0 or fraction > 1:
            await update.message.reply_text(
                "❌ **Invalid fraction.** Must be between 0 and 1.",
                parse_mode='Markdown'
            )
            return
        
        # Get trader info
        sdk_client = get_sdk_client()
        client = sdk_client.get_client()
        trader_address = client.get_trader_address()
        
        if not trader_address:
            await update.message.reply_text(
                "❌ **No trader configured.** Please configure your private key or AWS KMS.",
                parse_mode='Markdown'
            )
            return
        
        # Get positions to find the specific trade
        positions_manager = get_positions_manager()
        trades, _ = await positions_manager.get_trades(trader_address)
        
        # Find the specific trade
        target_trade = None
        for trade in trades:
            if trade.pair_index == pair_index and trade.index == trade_index:
                target_trade = trade
                break
        
        if not target_trade:
            await update.message.reply_text(
                f"❌ **Position not found.** No position with pair_index={pair_index} and trade_index={trade_index}.",
                parse_mode='Markdown'
            )
            return
        
        # Close position
        if fraction == 1.0:
            result = await positions_manager.close_full(trader_address, target_trade)
            close_type = "full"
        else:
            result = await positions_manager.close_partial(trader_address, target_trade, fraction)
            close_type = f"{fraction*100:.0f}% partial"
        
        if result.success:
            response = f"✅ **Position Closed Successfully**\n\n"
            response += f"**Close Type:** `{close_type}`\n"
            response += f"**Pair Index:** `{pair_index}`\n"
            response += f"**Trade Index:** `{trade_index}`\n"
            
            if result.closed_collateral:
                response += f"**Closed Collateral:** `{result.closed_collateral:.2f} USDC`\n"
            
            response += f"\n**Transaction:** `{result.tx_hash}`"
            
            await update.message.reply_text(response, parse_mode='Markdown')
        else:
            await update.message.reply_text(
                f"❌ **Failed to close position:** {result.error}",
                parse_mode='Markdown'
            )
        
    except ValueError as e:
        await update.message.reply_text(
            "❌ **Invalid number format.** Please check your input values.",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"❌ Error in a_close_handler: {e}")
        await update.message.reply_text(
            "❌ **Error closing position.** Please try again later.",
            parse_mode='Markdown'
        )


async def a_pairs_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /a_pairs command - List available trading pairs
    """
    try:
        # Get price provider
        price_provider = get_price_provider()
        
        # Get available pairs
        pairs = await price_provider.get_available_pairs()
        
        if not pairs:
            await update.message.reply_text(
                "❌ **No trading pairs available.** Please check your SDK connection.",
                parse_mode='Markdown'
            )
            return
        
        # Format response
        response = f"📊 **Available Trading Pairs** ({len(pairs)} total)\n\n"
        
        # Group pairs by category for better readability
        crypto_pairs = [p for p in pairs if any(crypto in p for crypto in ['BTC', 'ETH', 'SOL', 'AVAX', 'MATIC'])]
        other_pairs = [p for p in pairs if p not in crypto_pairs]
        
        if crypto_pairs:
            response += "**Popular Cryptocurrencies:**\n"
            for pair in crypto_pairs[:10]:  # Show max 10 crypto pairs
                response += f"• `{pair}`\n"
        
        if other_pairs:
            response += f"\n**Other Pairs:**\n"
            for pair in other_pairs[:10]:  # Show max 10 other pairs
                response += f"• `{pair}`\n"
        
        if len(pairs) > 20:
            response += f"\n... and {len(pairs) - 20} more pairs"
        
        response += f"\n\n**Usage:** Use `/a_price <PAIR>` to get detailed information."
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"❌ Error in a_pairs_handler: {e}")
        await update.message.reply_text(
            "❌ **Error getting trading pairs.** Please try again later.",
            parse_mode='Markdown'
        )


async def a_info_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /a_info command - Get trader information
    """
    try:
        # Get trader info
        sdk_client = get_sdk_client()
        client = sdk_client.get_client()
        trader_address = client.get_trader_address()
        
        if not trader_address:
            await update.message.reply_text(
                "❌ **No trader configured.** Please configure your private key or AWS KMS.",
                parse_mode='Markdown'
            )
            return
        
        # Get detailed trader info
        executor = get_executor()
        trader_info = await executor.get_trader_info()
        
        if not trader_info:
            await update.message.reply_text(
                "❌ **Error getting trader information.** Please try again later.",
                parse_mode='Markdown'
            )
            return
        
        # Format response
        response = f"👤 **Trader Information**\n\n"
        response += f"**Address:** `{trader_info['address']}`\n"
        response += f"**Chain ID:** `{trader_info['chain_id']}`\n\n"
        response += f"**Balances:**\n"
        response += f"• ETH: `{trader_info['eth_balance']:.4f}`\n"
        response += f"• USDC: `{trader_info['usdc_balance']:.2f}`\n"
        response += f"• USDC Allowance: `{trader_info['usdc_allowance']:.2f}`\n\n"
        response += f"**Status:** {'✅ Ready for trading' if trader_info['usdc_allowance'] > 0 else '⚠️ USDC allowance needed'}"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"❌ Error in a_info_handler: {e}")
        await update.message.reply_text(
            "❌ **Error getting trader information.** Please try again later.",
            parse_mode='Markdown'
        )


async def a_execmode_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /a_execmode command - Admin-only execution mode toggle
    
    Usage: /a_execmode <DRY|LIVE>
    """
    try:
        # Check if user is admin (simple check for now)
        user_id = update.effective_user.id
        admin_ids = os.getenv('ADMIN_USER_IDS', '').split(',')
        admin_ids = [int(uid.strip()) for uid in admin_ids if uid.strip()]
        
        if user_id not in admin_ids:
            await update.message.reply_text(
                "❌ **Admin only.** This command requires admin privileges.",
                parse_mode='Markdown'
            )
            return
        
        if not context.args:
            current_mode = get_execution_mode()
            await update.message.reply_text(
                f"🔧 **Current Execution Mode:** `{current_mode}`\n\n"
                f"**Usage:** `/a_execmode <DRY|LIVE>`\n\n"
                f"• `DRY` - Simulation mode (no real trades)\n"
                f"• `LIVE` - Real trading mode (⚠️ executes actual trades)",
                parse_mode='Markdown'
            )
            return
        
        mode = context.args[0].upper()
        success = set_execution_mode(mode)
        
        if success:
            mode_emoji = "⚠️" if mode == "LIVE" else "🔍"
            await update.message.reply_text(
                f"{mode_emoji} **Execution Mode Changed**\n\n"
                f"**New Mode:** `{mode}`\n"
                f"**Status:** {'Real trades will be executed!' if mode == 'LIVE' else 'Simulation mode active'}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ **Invalid mode.** Use `DRY` or `LIVE`.",
                parse_mode='Markdown'
            )
        
    except Exception as e:
        logger.error(f"❌ Error in a_execmode_handler: {e}")
        await update.message.reply_text(
            "❌ **Error changing execution mode.** Please try again later.",
            parse_mode='Markdown'
        )


async def alfa_debug_feeds_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /alfa debug:feeds command - Show feed status and last prices
    """
    try:
        from src.integrations.avantis.feed_client import get_feed_client
        
        feed_client = get_feed_client()
        price_provider = get_price_provider()
        
        response = "🔧 **Feed Debug Information**\n\n"
        
        # Feed client status
        if feed_client.is_configured():
            response += f"**Feed Status:** {'🟢 Running' if feed_client._running else '🔴 Stopped'}\n"
            response += f"**WebSocket:** `{feed_client.ws_url}`\n\n"
            
            # Last prices from cache
            if price_provider.latest_price:
                response += "**Last Prices:**\n"
                for pair, price in price_provider.latest_price.items():
                    response += f"• `{pair}`: ${price:.4f}\n"
            else:
                response += "**Last Prices:** No data available\n"
        else:
            response += "**Feed Status:** ❌ Not configured\n"
            response += "**WebSocket:** Not set\n"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"❌ Error in alfa_debug_feeds_handler: {e}")
        await update.message.reply_text(
            "❌ **Error getting feed information.** Please try again later.",
            parse_mode='Markdown'
        )


# Command handlers list for registration
avantis_handlers = [
    ("a_price", a_price_handler),
    ("a_open", a_open_handler),
    ("a_trades", a_trades_handler),
    ("a_close", a_close_handler),
    ("a_pairs", a_pairs_handler),
    ("a_info", a_info_handler),
    ("a_execmode", a_execmode_handler),
    ("alfa_debug_feeds", alfa_debug_feeds_handler),
]
