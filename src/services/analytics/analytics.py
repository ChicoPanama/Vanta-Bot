from datetime import datetime, timedelta
from typing import Any, Dict

from src.database.operations import db
from src.services.base_service import BaseService
from src.services.cache_service import cached
from src.utils.logging import get_logger

logger = get_logger(__name__)


class AnalyticsService(BaseService):
    """Enhanced analytics service with async database access."""

    @cached(ttl=300, key_prefix="analytics")
    async def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive user trading statistics."""
        self.log_operation("get_user_stats", user_id)

        positions = await db.get_user_positions(user_id)
        closed_positions = [pos for pos in positions if pos.status == "CLOSED"]

        total_trades = len(closed_positions)
        winning_trades = sum(1 for pos in closed_positions if (pos.pnl or 0) > 0)
        losing_trades = sum(1 for pos in closed_positions if (pos.pnl or 0) < 0)

        total_pnl = float(sum(pos.pnl or 0 for pos in closed_positions))
        avg_win_values = [pos.pnl for pos in closed_positions if (pos.pnl or 0) > 0]
        avg_loss_values = [pos.pnl for pos in closed_positions if (pos.pnl or 0) < 0]

        avg_win = float(sum(avg_win_values) / len(avg_win_values)) if avg_win_values else 0.0
        avg_loss = float(sum(avg_loss_values) / len(avg_loss_values)) if avg_loss_values else 0.0

        win_rate = (winning_trades / total_trades * 100) if total_trades else 0.0
        profit_factor = abs(avg_win / avg_loss) if avg_loss else 0.0

        return {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
        }

    @cached(ttl=180, key_prefix="portfolio")
    async def get_portfolio_summary(self, user_id: int) -> Dict[str, Any]:
        """Get portfolio summary with current positions."""
        self.log_operation("get_portfolio_summary", user_id)

        open_positions = await db.get_user_positions(user_id, status="OPEN")
        total_unrealized_pnl = float(sum(pos.pnl or 0 for pos in open_positions))
        total_exposure = float(sum((pos.size or 0) * (pos.leverage or 0) for pos in open_positions))

        return {
            "open_positions": len(open_positions),
            "total_unrealized_pnl": total_unrealized_pnl,
            "total_exposure": total_exposure,
            "positions": [
                {
                    "symbol": pos.symbol,
                    "side": pos.side,
                    "size": float(pos.size or 0),
                    "leverage": pos.leverage,
                    "pnl": float(pos.pnl or 0),
                    "entry_price": float(pos.entry_price or 0),
                    "current_price": float(pos.current_price or 0),
                }
                for pos in open_positions
            ],
        }

    async def get_performance_metrics(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get performance metrics for a specific period."""
        self.log_operation("get_performance_metrics", user_id, days=days)

        cutoff = datetime.utcnow() - timedelta(days=days)
        positions = await db.get_user_positions(user_id)
        closed_recent = [
            pos
            for pos in positions
            if pos.status == "CLOSED" and (pos.closed_at or pos.opened_at or datetime.utcnow()) >= cutoff
        ]

        if not closed_recent:
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

        trades = len(closed_recent)
        pnl_values = [float(pos.pnl or 0) for pos in closed_recent]
        total_pnl = sum(pnl_values)
        winning_trades = sum(1 for pnl in pnl_values if pnl > 0)
        win_rate = (winning_trades / trades * 100) if trades else 0.0
        avg_return = total_pnl / trades if trades else 0.0

        if len(pnl_values) > 1:
            mean = total_pnl / len(pnl_values)
            variance = sum((p - mean) ** 2 for p in pnl_values) / (len(pnl_values) - 1)
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

    def validate_input(self, data: Dict[str, Any]) -> bool:
        """Validate input data."""
        return isinstance(data, dict) and isinstance(data.get("user_id"), int)


class Analytics(AnalyticsService):
    """Backward compatibility wrapper."""

    pass
