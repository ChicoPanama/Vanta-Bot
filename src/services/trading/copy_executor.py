"""
Copy Trading Executor
Provides auto-copy functionality for followed traders
"""
from __future__ import annotations
import logging
from typing import Dict, Any, Optional
from decimal import Decimal

from src.services.trading.execution_service import get_execution_service
from src.config.settings_new import settings

log = logging.getLogger(__name__)

async def follow(
    user_id: int,
    trader_key: str,
    pair: str,
    side: str,
    leverage: float,
    collateral_usdc: float,
    slippage_pct: Optional[float] = None
) -> Dict[str, Any]:
    """
    Execute a copy trade based on a followed trader's signal
    
    Args:
        user_id: Telegram user ID
        trader_key: Trader identifier (wallet address or ID)
        pair: Trading pair (e.g., "ETH/USD")
        side: "LONG" or "SHORT"
        leverage: Leverage multiplier
        collateral_usdc: Collateral amount in USDC
        slippage_pct: Optional slippage override
        
    Returns:
        Dict with execution result
    """
    try:
        log.info(f"Copy executing trade for user {user_id}: {pair} {side} {leverage}x ${collateral_usdc}")
        
        # Get execution service
        svc = get_execution_service(settings)
        
        # Create a draft for the copy trade
        from src.services.trading.trade_drafts import TradeDraft
        draft = TradeDraft(
            user_id=user_id,
            pair=pair,
            side=side,
            collateral_usdc=Decimal(str(collateral_usdc)),
            leverage=Decimal(str(leverage)),
        )
        
        # Execute the trade
        ok, msg, result = await svc.execute_open(
            draft=draft,
            slippage_pct=Decimal(str(slippage_pct)) if slippage_pct is not None else None
        )
        
        return {
            "success": ok,
            "message": msg,
            "result": result,
            "trader_key": trader_key,
            "pair": pair,
            "side": side,
            "leverage": leverage,
            "collateral_usdc": collateral_usdc
        }
        
    except Exception as e:
        log.exception(f"Copy execution failed for user {user_id}, trader {trader_key}: {e}")
        return {
            "success": False,
            "message": f"Copy execution failed: {str(e)}",
            "result": None,
            "trader_key": trader_key,
            "error": str(e)
        }

async def status(user_id: int, trader_key: str) -> Dict[str, Any]:
    """
    Get copy trading status for a user-trader pair
    
    Args:
        user_id: Telegram user ID
        trader_key: Trader identifier
        
    Returns:
        Dict with status information
    """
    try:
        # For now, return basic status
        # In the future, this could check active positions, PnL, etc.
        return {
            "ok": True,
            "user_id": user_id,
            "trader_key": trader_key,
            "active_copies": 0,  # TODO: count active positions from this trader
            "total_pnl": 0.0,    # TODO: calculate PnL from copy trades
            "last_copy_at": None # TODO: timestamp of last copy trade
        }
    except Exception as e:
        log.exception(f"Status check failed for user {user_id}, trader {trader_key}: {e}")
        return {
            "ok": False,
            "error": str(e)
        }
