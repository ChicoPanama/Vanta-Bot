"""Portfolio Service business logic using async database helpers."""

from datetime import datetime, timedelta
from typing import Any

from src.database.operations import db
from src.services.base_service import BaseService


class PortfolioService(BaseService):
    """Service for portfolio management and analytics."""

    async def get_portfolio_summary(self, user_id: int) -> dict[str, Any]:
        """Get comprehensive portfolio summary."""
        self.log_operation("get_portfolio_summary", user_id)

        positions = await db.get_user_positions(user_id)
        open_positions = [pos for pos in positions if pos.status == "OPEN"]
        closed_positions = [pos for pos in positions if pos.status == "CLOSED"]

        total_trades = len(closed_positions)
        winning_trades = sum(1 for pos in closed_positions if (pos.pnl or 0) > 0)
        losing_trades = sum(1 for pos in closed_positions if (pos.pnl or 0) < 0)

        win_rate = (winning_trades / total_trades * 100) if total_trades else 0.0
        total_pnl = float(sum(pos.pnl or 0 for pos in closed_positions))
        unrealized_pnl = float(sum(pos.pnl or 0 for pos in open_positions))

        total_volume = float(
            sum((pos.size or 0) * (pos.leverage or 0) for pos in positions)
        )
        total_exposure = float(
            sum((pos.size or 0) * (pos.leverage or 0) for pos in open_positions)
        )

        avg_win_values = [pos.pnl for pos in closed_positions if (pos.pnl or 0) > 0]
        avg_loss_values = [pos.pnl for pos in closed_positions if (pos.pnl or 0) < 0]
        avg_win = (
            float(sum(avg_win_values) / len(avg_win_values)) if avg_win_values else 0.0
        )
        avg_loss = (
            float(sum(avg_loss_values) / len(avg_loss_values))
            if avg_loss_values
            else 0.0
        )
        profit_factor = abs(avg_win / avg_loss) if avg_loss else 0.0

        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_positions = [
            pos
            for pos in closed_positions
            if (pos.closed_at or pos.opened_at or datetime.utcnow()) >= thirty_days_ago
        ]
        recent_pnl = float(sum(pos.pnl or 0 for pos in recent_positions))

        return {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "unrealized_pnl": unrealized_pnl,
            "total_volume": total_volume,
            "total_exposure": total_exposure,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "best_trade": float(
                max((pos.pnl or 0) for pos in closed_positions)
                if closed_positions
                else 0.0
            ),
            "worst_trade": float(
                min((pos.pnl or 0) for pos in closed_positions)
                if closed_positions
                else 0.0
            ),
            "recent_trades": len(recent_positions),
            "recent_pnl": recent_pnl,
            "open_positions_count": len(open_positions),
            "positions": [
                {
                    "id": pos.id,
                    "symbol": pos.symbol,
                    "side": pos.side,
                    "size": float(pos.size or 0),
                    "leverage": pos.leverage,
                    "entry_price": float(pos.entry_price or 0),
                    "current_price": float(pos.current_price or 0),
                    "pnl": float(pos.pnl or 0),
                    "status": pos.status,
                    "opened_at": (pos.opened_at or datetime.utcnow()).isoformat(),
                }
                for pos in open_positions
            ],
        }

    async def get_performance_metrics(
        self, user_id: int, days: int = 30
    ) -> dict[str, Any]:
        """Get performance metrics for a specific period."""
        self.log_operation("get_performance_metrics", user_id, days=days)

        cutoff_date = datetime.utcnow() - timedelta(days=days)
        positions = await db.get_user_positions(user_id)
        recent_closed = [
            pos
            for pos in positions
            if pos.status == "CLOSED"
            and (pos.closed_at or pos.opened_at or datetime.utcnow()) >= cutoff_date
        ]

        if not recent_closed:
            return {
                "period_days": days,
                "trades": 0,
                "total_pnl": 0.0,
                "win_rate": 0.0,
                "avg_return": 0.0,
                "volatility": 0.0,
                "best_trade": 0.0,
                "worst_trade": 0.0,
            }

        trades = len(recent_closed)
        pnl_values = [float(pos.pnl or 0) for pos in recent_closed]
        total_pnl = sum(pnl_values)
        winning_trades = sum(1 for pnl in pnl_values if pnl > 0)
        win_rate = (winning_trades / trades * 100) if trades else 0.0
        avg_return = total_pnl / trades if trades else 0.0

        if len(pnl_values) > 1:
            mean_return = total_pnl / len(pnl_values)
            variance = sum((p - mean_return) ** 2 for p in pnl_values) / (
                len(pnl_values) - 1
            )
            volatility = variance**0.5
        else:
            volatility = 0.0

        return {
            "period_days": days,
            "trades": trades,
            "total_pnl": total_pnl,
            "win_rate": win_rate,
            "avg_return": avg_return,
            "volatility": volatility,
            "best_trade": max(pnl_values),
            "worst_trade": min(pnl_values),
        }

    async def get_asset_breakdown(self, user_id: int) -> dict[str, Any]:
        """Get portfolio breakdown by asset."""
        self.log_operation("get_asset_breakdown", user_id)

        positions = await db.get_user_positions(user_id)
        asset_stats: dict[str, dict[str, Any]] = {}

        for pos in positions:
            symbol = pos.symbol or "UNKNOWN"
            stats = asset_stats.setdefault(
                symbol,
                {
                    "total_trades": 0,
                    "winning_trades": 0,
                    "total_pnl": 0.0,
                    "total_volume": 0.0,
                },
            )

            stats["total_trades"] += 1
            stats["total_pnl"] += float(pos.pnl or 0)
            stats["total_volume"] += float((pos.size or 0) * (pos.leverage or 0))
            if pos.status == "CLOSED" and (pos.pnl or 0) > 0:
                stats["winning_trades"] += 1

        for stats in asset_stats.values():
            trades = stats["total_trades"] or 1
            stats["win_rate"] = (stats["winning_trades"] / trades) * 100
            stats["avg_leverage"] = stats["total_volume"] / trades

        return asset_stats

    def validate_input(self, data: dict[str, Any]) -> bool:
        """Validate portfolio input data."""
        return isinstance(data, dict) and isinstance(data.get("user_id"), int)
