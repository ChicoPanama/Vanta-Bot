"""
Copy Trading Executor
Provides auto-copy functionality for followed traders
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, case, func, select

from src.config.settings import settings
from src.database import models
from src.database.operations import db
from src.services.trading.execution_service import get_execution_service

log = logging.getLogger(__name__)


async def follow(
    user_id: int,
    trader_key: str,
    pair: str,
    side: str,
    leverage: float,
    collateral_usdc: float,
    slippage_pct: float | None = None,
) -> dict[str, Any]:
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
        log.info(
            f"Copy executing trade for user {user_id}: {pair} {side} {leverage}x ${collateral_usdc}"
        )

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
            slippage_pct=Decimal(str(slippage_pct))
            if slippage_pct is not None
            else None,
        )

        return {
            "success": ok,
            "message": msg,
            "result": result,
            "trader_key": trader_key,
            "pair": pair,
            "side": side,
            "leverage": leverage,
            "collateral_usdc": collateral_usdc,
        }

    except Exception as e:
        log.exception(
            f"Copy execution failed for user {user_id}, trader {trader_key}: {e}"
        )
        return {
            "success": False,
            "message": f"Copy execution failed: {str(e)}",
            "result": None,
            "trader_key": trader_key,
            "error": str(e),
        }


def _ts_to_iso(value):
    if value in (None, 0):
        return None
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()
    except Exception:  # pragma: no cover - best effort formatting
        return None


async def status(user_id: int, trader_key: str) -> dict[str, Any]:
    """
    Get copy trading status for a user-trader pair

    Args:
        user_id: Telegram user ID
        trader_key: Trader identifier

    Returns:
        Dict with status information
    """
    try:
        cutoff_ts = int((datetime.now(timezone.utc) - timedelta(days=30)).timestamp())

        async def _load(session):
            filters = [models.CopyPosition.user_id == user_id]
            if trader_key != "*":
                filters.append(models.CopyPosition.leader_address == trader_key.lower())

            volume_expr = models.CopyPosition.size * models.CopyPosition.entry_price
            closed_filter = models.CopyPosition.status == "CLOSED"
            open_filter = models.CopyPosition.status == "OPEN"
            recent_filter = models.CopyPosition.opened_at >= cutoff_ts
            recent_closed_filter = and_(closed_filter, recent_filter)

            aggregate_stmt = select(
                func.coalesce(
                    func.sum(case((closed_filter, models.CopyPosition.pnl), else_=0)), 0
                ).label("total_pnl"),
                func.coalesce(
                    func.sum(case((closed_filter, volume_expr), else_=0)), 0
                ).label("closed_volume"),
                func.coalesce(
                    func.sum(case((open_filter, volume_expr), else_=0)), 0
                ).label("open_volume"),
                func.coalesce(func.sum(case((closed_filter, 1), else_=0)), 0).label(
                    "closed_count"
                ),
                func.coalesce(
                    func.sum(
                        case(
                            (and_(closed_filter, models.CopyPosition.pnl > 0), 1),
                            else_=0,
                        )
                    ),
                    0,
                ).label("wins"),
                func.coalesce(
                    func.sum(
                        case((recent_closed_filter, models.CopyPosition.pnl), else_=0)
                    ),
                    0,
                ).label("pnl_30d"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                and_(recent_closed_filter, models.CopyPosition.pnl > 0),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("wins_30d"),
                func.coalesce(
                    func.sum(case((recent_closed_filter, 1), else_=0)), 0
                ).label("closed_30d"),
                func.coalesce(
                    func.sum(
                        case((and_(recent_filter, open_filter), volume_expr), else_=0)
                    ),
                    0,
                ).label("open_volume_30d"),
                func.coalesce(
                    func.sum(
                        case((and_(recent_filter, closed_filter), volume_expr), else_=0)
                    ),
                    0,
                ).label("closed_volume_30d"),
                func.coalesce(func.sum(case((open_filter, 1), else_=0)), 0).label(
                    "open_count"
                ),
                func.max(models.CopyPosition.opened_at).label("last_opened"),
                func.max(models.CopyPosition.closed_at).label("last_closed"),
            ).where(*filters)

            return (await session.execute(aggregate_stmt)).one()

        summary = await db.run_in_session(_load)

        total_pnl = float(summary.total_pnl or 0.0)
        open_volume = float(summary.open_volume or 0.0)
        closed_volume = float(summary.closed_volume or 0.0)
        total_volume = open_volume + closed_volume
        pnl_30d = float(summary.pnl_30d or 0.0)
        open_volume_30d = float(summary.open_volume_30d or 0.0)
        closed_volume_30d = float(summary.closed_volume_30d or 0.0)
        volume_30d = open_volume_30d + closed_volume_30d
        active_copies = int(summary.open_count or 0)
        closed_count = int(summary.closed_count or 0)
        wins = int(summary.wins or 0)
        win_rate = (wins / closed_count * 100.0) if closed_count else 0.0
        closed_30d = int(summary.closed_30d or 0)
        wins_30d = int(summary.wins_30d or 0)
        win_rate_30d = (wins_30d / closed_30d * 100.0) if closed_30d else 0.0

        return {
            "ok": True,
            "user_id": user_id,
            "trader_key": trader_key,
            "active_copies": active_copies,
            "total_pnl": total_pnl,
            "total_volume": total_volume,
            "open_volume": open_volume,
            "closed_volume": closed_volume,
            "pnl_30d": pnl_30d,
            "volume_30d": volume_30d,
            "open_volume_30d": open_volume_30d,
            "closed_volume_30d": closed_volume_30d,
            "win_rate": win_rate,
            "win_rate_30d": win_rate_30d,
            "last_copy_at": _ts_to_iso(summary.last_opened),
            "last_closed_at": _ts_to_iso(summary.last_closed),
            "closed_copies": closed_count,
            "wins": wins,
            "wins_30d": wins_30d,
            "closed_copies_30d": closed_30d,
        }
    except Exception as e:
        log.exception(
            f"Status check failed for user {user_id}, trader {trader_key}: {e}"
        )
        return {"ok": False, "error": str(e)}
