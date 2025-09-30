"""Analytics-backed insights service powering AI bot handlers."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import mean
from typing import Any

from sqlalchemy import func, select

from src.database import models
from src.database.operations import db
from src.services.base_service import BaseService


def _safe_mean(values: Iterable[float]) -> float:
    items = [v for v in values if v is not None]
    return float(mean(items)) if items else 0.0


@dataclass
class _Signal:
    symbol: str
    average_pnl: float
    total_pnl: float
    trades: int

    @property
    def sentiment(self) -> str:
        if self.average_pnl > 50:
            return "green"
        if self.average_pnl < -25:
            return "red"
        return "yellow"

    @property
    def confidence(self) -> float:
        base = min(1.0, self.trades / 20)
        modifier = 0.2 if abs(self.average_pnl) > 75 else 0.0
        return round(min(0.95, base + modifier), 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "signal": self.sentiment,
            "confidence": self.confidence,
            "avg_pnl": self.average_pnl,
            "total_pnl": self.total_pnl,
            "trades": self.trades,
        }


class InsightsService(BaseService):
    """Generate leaderboard, market signals, and trader analytics from DB state."""

    # BaseService contract: simple permissive validation for analytics fetches
    def validate_input(self, data: dict[str, Any]) -> bool:  # type: ignore[override]
        return True

    async def get_leaderboard(self, limit: int = 10) -> list[dict[str, Any]]:
        self.log_operation("get_leaderboard", limit=limit)

        async def _query(session):
            stmt = (
                select(
                    models.User.id,
                    models.User.username,
                    models.User.telegram_id,
                    func.count(models.Position.id).label("trade_count"),
                    func.sum(models.Position.pnl).label("total_pnl"),
                    func.avg(models.Position.pnl).label("avg_pnl"),
                    func.sum(models.Position.size * models.Position.leverage).label(
                        "notional"
                    ),
                    func.max(models.Position.closed_at).label("last_trade_at"),
                )
                .join(models.Position, models.Position.user_id == models.User.id)
                .where(models.Position.status == "CLOSED")
                .group_by(models.User.id, models.User.username, models.User.telegram_id)
                .order_by(func.sum(models.Position.pnl).desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            return result.all()

        rows = await db.run_in_session(_query)
        leaderboard: list[dict[str, Any]] = []
        for row in rows:
            user_id = row.id
            handle = (
                f"@{row.username}"
                if row.username
                else (f"tg:{row.telegram_id}" if row.telegram_id else f"user:{user_id}")
            )
            trade_count = int(row.trade_count or 0)
            total_pnl = float(row.total_pnl or 0.0)
            notional = float(row.notional or 0.0)
            avg_ticket = notional / trade_count if trade_count else 0.0

            archetype = self._derive_archetype(trade_count, avg_ticket)
            risk_level = self._assess_risk(trade_count, avg_ticket)
            score = self._score_copyability(total_pnl, trade_count, avg_ticket)

            leaderboard.append(
                {
                    "address": handle,
                    "user_id": user_id,
                    "trade_count": trade_count,
                    "total_pnl": total_pnl,
                    "average_pnl": float(row.avg_pnl or 0.0),
                    "notional": notional,
                    "last_trade_at": self._format_ts(row.last_trade_at),
                    "copyability_score": score,
                    "archetype": archetype,
                    "risk_level": risk_level,
                }
            )

        return leaderboard

    async def get_market_signal(self) -> dict[str, Any]:
        self.log_operation("get_market_signal")

        async def _query(session):
            stmt = select(
                models.Position.symbol,
                models.Position.pnl,
                models.Position.size,
                models.Position.leverage,
                models.Position.opened_at,
            ).where(models.Position.status == "OPEN")
            result = await session.execute(stmt)
            return result.all()

        open_positions = await db.run_in_session(_query)
        if not open_positions:
            return {
                "signal": "yellow",
                "confidence": 0.2,
                "timeframe": "24h",
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "reasoning": "No open positions recorded yet",
            }

        pnls = [float(row.pnl or 0.0) for row in open_positions]
        avg_pnl = _safe_mean(pnls)
        vol = self._compute_volatility(pnls)

        if avg_pnl > 50 and vol < 75:
            signal = "green"
        elif avg_pnl < -25:
            signal = "red"
        else:
            signal = "yellow"

        confidence = min(0.95, max(0.25, len(open_positions) / 10))
        reasoning = f"Average open PnL {avg_pnl:.0f} USD across {len(open_positions)} positions, volatility {vol:.0f}"

        return {
            "signal": signal,
            "confidence": confidence,
            "timeframe": "24h",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "reasoning": reasoning,
        }

    async def get_copy_opportunities(self) -> list[dict[str, Any]]:
        self.log_operation("get_copy_opportunities")
        leaderboard = await self.get_leaderboard(limit=20)
        opportunities: list[dict[str, Any]] = []

        for entry in leaderboard:
            if entry["copyability_score"] < 40:
                continue
            opportunities.append(
                {
                    "trader": {
                        "address": entry["address"],
                        "trade_count": entry["trade_count"],
                    },
                    "opportunity_score": entry["copyability_score"],
                    "reason": self._build_opportunity_reason(entry),
                }
            )
            if len(opportunities) >= 5:
                break

        return opportunities

    async def get_dashboard(self) -> dict[str, Any]:
        self.log_operation("get_dashboard")
        signals = await self._collect_signals()
        market_signal = await self.get_market_signal()

        top_signals = [signal.to_dict() for signal in signals[:3]]
        positive = sum(1 for s in signals if s.sentiment == "green")
        neutral = sum(1 for s in signals if s.sentiment == "yellow")
        negative = sum(1 for s in signals if s.sentiment == "red")
        total = max(1, positive + neutral + negative)

        if positive / total >= 0.6:
            regime = "favorable"
        elif negative / total >= 0.5:
            regime = "risky"
        else:
            regime = "mixed"

        confidence = round(
            min(0.95, market_signal["confidence"] + len(signals) * 0.02), 2
        )

        return {
            "regime": regime,
            "confidence": confidence,
            "signals": top_signals,
        }

    async def get_market_analysis(self) -> dict[str, Any]:
        self.log_operation("get_market_analysis")
        signals = await self._collect_signals()
        if not signals:
            return {
                "sentiment": "unknown",
                "volatility": "n/a",
                "trend": "n/a",
                "key_insights": [],
            }

        avg_pnl = _safe_mean(signal.average_pnl for signal in signals)
        volatility = _safe_mean(abs(signal.average_pnl) for signal in signals)

        if avg_pnl > 25:
            sentiment = "positive"
        elif avg_pnl < -15:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        if volatility > 150:
            trend = "high-volatility"
        elif avg_pnl > 25:
            trend = "uptrend"
        elif avg_pnl < -15:
            trend = "downtrend"
        else:
            trend = "sideways"

        key_insights = []
        for signal in signals[:3]:
            key_insights.append(
                f"{signal.symbol}: {signal.sentiment.upper()} with avg PnL {signal.average_pnl:.0f} USD"
            )

        return {
            "sentiment": sentiment,
            "volatility": f"{volatility:.0f} USD",
            "trend": trend,
            "key_insights": key_insights,
        }

    async def get_trader_analytics_summary(self) -> dict[str, Any]:
        self.log_operation("get_trader_analytics_summary")

        async def _query(session):
            stmt = select(
                models.Position.user_id,
                func.count(models.Position.id).label("trade_count"),
                func.sum(models.Position.pnl).label("total_pnl"),
                func.avg(models.Position.pnl).label("avg_pnl"),
            ).group_by(models.Position.user_id)
            result = await session.execute(stmt)
            return result.all()

        rows = await db.run_in_session(_query)
        if not rows:
            return {
                "total_traders": 0,
                "active_traders": 0,
                "avg_performance": 0.0,
                "top_archetypes": [],
            }

        archetype_counts: dict[str, int] = defaultdict(int)
        active = 0
        performances: list[float] = []

        for row in rows:
            trade_count = int(row.trade_count or 0)
            total_pnl = float(row.total_pnl or 0.0)
            avg_ticket = total_pnl / trade_count if trade_count else 0.0
            archetype = self._derive_archetype(trade_count, abs(avg_ticket))
            archetype_counts[archetype] += 1
            if trade_count > 0:
                active += 1
            if trade_count:
                performances.append(total_pnl / trade_count)

        top_archetypes = [
            f"{name} ({count})"
            for name, count in sorted(
                archetype_counts.items(), key=lambda x: x[1], reverse=True
            )[:3]
        ]

        return {
            "total_traders": len(rows),
            "active_traders": active,
            "avg_performance": _safe_mean(performances)
            / 100,  # convert to percentage-ish scale
            "top_archetypes": top_archetypes,
        }

    async def _collect_signals(self) -> list[_Signal]:
        async def _query(session):
            stmt = (
                select(
                    models.Position.symbol,
                    func.count(models.Position.id).label("trade_count"),
                    func.sum(models.Position.pnl).label("total_pnl"),
                    func.avg(models.Position.pnl).label("avg_pnl"),
                )
                .where(models.Position.symbol.isnot(None))
                .group_by(models.Position.symbol)
                .order_by(func.sum(models.Position.pnl).desc())
            )
            result = await session.execute(stmt)
            return result.all()

        rows = await db.run_in_session(_query)
        signals: list[_Signal] = []
        for row in rows:
            if row.symbol is None:
                continue
            signals.append(
                _Signal(
                    symbol=row.symbol,
                    trades=int(row.trade_count or 0),
                    total_pnl=float(row.total_pnl or 0.0),
                    average_pnl=float(row.avg_pnl or 0.0),
                )
            )
        return signals

    @staticmethod
    def _compute_volatility(values: Iterable[float]) -> float:
        items = [v for v in values if v is not None]
        if len(items) < 2:
            return 0.0
        avg = sum(items) / len(items)
        variance = sum((v - avg) ** 2 for v in items) / len(items)
        return variance**0.5

    @staticmethod
    def _format_ts(value: datetime | None) -> str | None:
        if not value:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()

    @staticmethod
    def _derive_archetype(trade_count: int, avg_ticket: float) -> str:
        if trade_count >= 500:
            return "High Frequency"
        if avg_ticket >= 50000:
            return "Whale"
        if trade_count >= 150:
            return "Active Trader"
        if trade_count >= 50:
            return "Swing Trader"
        return "Emerging"

    @staticmethod
    def _assess_risk(trade_count: int, avg_ticket: float) -> str:
        if avg_ticket >= 50000 or trade_count >= 400:
            return "HIGH"
        if avg_ticket >= 15000 or trade_count >= 150:
            return "MED"
        return "LOW"

    @staticmethod
    def _score_copyability(
        total_pnl: float, trade_count: int, avg_ticket: float
    ) -> int:
        pnl_score = min(40, max(-20, total_pnl / 1000))
        activity_score = min(35, trade_count * 0.2)
        discipline_bonus = 15 if 1000 <= avg_ticket <= 20000 else 5
        raw = max(0, pnl_score + activity_score + discipline_bonus)
        return int(min(100, raw))

    @staticmethod
    def _build_opportunity_reason(entry: dict[str, Any]) -> str:
        return f"Consistent performance: {entry['trade_count']} trades with total PnL ${entry['total_pnl']:,.0f}."
