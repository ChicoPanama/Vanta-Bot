# src/bot/handlers/alfa_handlers.py
from __future__ import annotations
from typing import Optional
import os
import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from sqlalchemy import create_engine

from src.services.analytics.leaderboard_service import LeaderboardService
from src.services.contracts.avantis_registry import get_registry

logger = logging.getLogger(__name__)

# Global service instances
_engine = None
_lb: Optional[LeaderboardService] = None

def _get_lb() -> LeaderboardService:
    """Get leaderboard service instance"""
    global _engine, _lb
    if _engine is None:
        database_url = os.getenv("DATABASE_URL", "sqlite:///vanta_bot.db")
        _engine = create_engine(database_url, pool_pre_ping=True)
    if _lb is None:
        _lb = LeaderboardService(_engine)
    return _lb

async def cmd_alfa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /alfa commands"""
    text = (update.message.text or "").strip()
    
    # Handle debug:contracts command
    if "debug:contracts" in text:
        await cmd_debug_contracts(update, context)
        return
    
    # Handle top50 command
    if "top50" not in text:
        await update.message.reply_text(
            "Usage: `/alfa top50` or `/alfa debug:contracts`\n\n"
            "• `top50` - Shows top 50 AI-ranked traders with clean PnL metrics\n"
            "• `debug:contracts` - Shows resolved contract addresses",
            parse_mode='Markdown'
        )
        return
    
    try:
        lb = _get_lb()
        rows = await lb.top_traders(limit=50)
        
        if not rows:
            await update.message.reply_text(
                "No leaders yet — indexing…\n\nTry again in a few minutes once the system has processed some trading data.",
                parse_mode='Markdown'
            )
            return

        lines = ["*Top 50 (30D)* — vol / median / clean PnL / last activity / score\n"]
        for i, r in enumerate(rows, 1):
            lines.append(
                f"{i:02d}. `{r['address']}` — "
                f"${float(r['last_30d_volume_usd']):,.0f} / "
                f"${float(r['median_trade_size_usd']):,.0f} / "
                f"${float(r['clean_realized_pnl_usd']):,.0f} / "
                f"{int(r['last_trade_at'])} / "
                f"score {r['copyability_score']}"
            )
        
        # Split message if too long (Telegram limit is 4096 chars)
        message = "\n".join(lines)
        if len(message) > 4000:
            # Send in chunks
            chunk_size = 3500
            for i in range(0, len(message), chunk_size):
                chunk = message[i:i + chunk_size]
                if i > 0:
                    chunk = f"*Top 50 (continued)* — vol / median / clean PnL / last activity / score\n" + chunk
                await update.message.reply_text(chunk, parse_mode='Markdown')
        else:
            await update.message.reply_text(message, parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"Error in alfa command: {e}")
        await update.message.reply_text(
            "❌ Error loading leaderboard. Please try again later.",
            parse_mode='Markdown'
        )


async def cmd_debug_contracts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /alfa debug:contracts command"""
    try:
        registry = get_registry()
        if not registry:
            await update.message.reply_text(
                "❌ Contract registry not initialized. Bot may still be starting up.",
                parse_mode='Markdown'
            )
            return
        
        contract_info = await registry.get_contract_info()
        
        message = (
            f"🔧 **Contract Registry Debug**\n\n"
            f"**Trading Contract:**\n"
            f"`{contract_info['trading_contract']}`\n\n"
            f"**Vault Contract:**\n"
            f"`{contract_info['vault_contract'] or 'Not resolved'}`\n\n"
            f"**Status:**\n"
            f"• Vault Resolved: {'✅' if contract_info['vault_resolved'] else '❌'}\n"
            f"• Network: {contract_info['network']}\n"
            f"• Chain ID: {contract_info['chain_id']}"
        )
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in debug:contracts command: {e}")
        await update.message.reply_text(
            "❌ Error retrieving contract information. Please try again later.",
            parse_mode='Markdown'
        )

# Export handler for registration
alfa_handlers = [
    CommandHandler("alfa", cmd_alfa),
]
