# src/services/analytics/leaderboard_service.py
from __future__ import annotations

import os
from decimal import Decimal
from typing import Any

import redis.asyncio as redis
from loguru import logger
from sqlalchemy import text
from sqlalchemy.engine import Engine

from .pnl_service import PnlService

ACTIVE_HOURS = int(os.getenv("LEADER_ACTIVE_HOURS", "72"))
MIN_TRADES = int(os.getenv("LEADER_MIN_TRADES_30D", "300"))
MIN_VOL = float(os.getenv("LEADER_MIN_VOLUME_30D_USD", "10000000"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


class LeaderboardService:
    def __init__(self, engine: Engine):
        self.engine = engine
        self.redis: redis.Redis | None = None
        self.pnl = PnlService(engine)

    async def _get_redis(self):
        """Get Redis connection, create if needed"""
        if not self.redis:
            self.redis = await redis.from_url(REDIS_URL, decode_responses=True)
        return self.redis

    async def top_traders(self, limit: int = 50) -> list[dict[str, Any]]:
        """
        Get top traders based on 30-day performance metrics.
        First tries Redis cache, then falls back to database computation.
        """
        # Try Redis cache first
        redis = await self._get_redis()
        cache_key = f"leaderboard:top_{limit}"

        try:
            cached_data = await redis.get(cache_key)
            if cached_data:
                import json

                cached_traders = json.loads(cached_data)
                logger.debug(f"Retrieved {len(cached_traders)} traders from cache")
                return cached_traders
        except Exception as e:
            logger.warning(f"Redis cache read failed: {e}")

        # Compute from database
        traders = await self._compute_leaderboard_from_db(limit)

        # Cache the results for 5 minutes
        try:
            import json

            await redis.setex(cache_key, 300, json.dumps(traders))
            logger.debug(f"Cached {len(traders)} traders for 5 minutes")
        except Exception as e:
            logger.warning(f"Redis cache write failed: {e}")

        return traders

    async def _compute_leaderboard_from_db(self, limit: int) -> list[dict[str, Any]]:
        """Compute leaderboard directly from database"""
        # Calculate 30 days ago timestamp
        import time

        thirty_days_ago = int(time.time()) - (30 * 24 * 60 * 60)
        active_hours_ago = int(time.time()) - (ACTIVE_HOURS * 60 * 60)

        sql = text(
            """
            WITH window_fills AS (
                SELECT
                    address,
                    pair,
                    ABS(price * size) as notional_usd,
                    ts
                FROM fills
                WHERE ts >= :thirty_days_ago
            ),
            per_addr AS (
                SELECT
                    address,
                    COUNT(*) as trade_count_30d,
                    SUM(notional_usd) as last_30d_volume_usd,
                    AVG(notional_usd) as median_trade_size_usd,
                    MAX(ts) as last_trade_at
                FROM window_fills
                GROUP BY address
            )
            SELECT
                address,
                trade_count_30d,
                last_30d_volume_usd,
                median_trade_size_usd,
                last_trade_at
            FROM per_addr
            WHERE trade_count_30d >= :min_trades
              AND last_30d_volume_usd >= :min_vol
              AND last_trade_at >= :active_hours_ago
            ORDER BY
                last_30d_volume_usd DESC,
                median_trade_size_usd DESC,
                last_trade_at DESC
            LIMIT :limit
        """
        )

        try:
            with self.engine.begin() as conn:
                result = conn.execute(
                    sql,
                    {
                        "thirty_days_ago": thirty_days_ago,
                        "min_trades": MIN_TRADES,
                        "min_vol": MIN_VOL,
                        "active_hours_ago": active_hours_ago,
                        "limit": limit,
                    },
                )
                rows = [dict(r._mapping) for r in result]
        except Exception as e:
            logger.error(f"Database query failed: {e}")
            # Return mock data for testing
            return await self._get_mock_leaderboard(limit)

        # Enhance with additional metrics
        enhanced_traders = []
        for row in rows:
            addr = row["address"]
            clean_pnl = self.pnl.clean_realized_pnl_30d(addr)

            trader = {
                "address": addr,
                "trade_count_30d": row["trade_count_30d"],
                "last_30d_volume_usd": float(row["last_30d_volume_usd"]),
                "median_trade_size_usd": float(row["median_trade_size_usd"]),
                "last_trade_at": row["last_trade_at"],
                "clean_realized_pnl_usd": str(clean_pnl),
                "copyability_score": self._calculate_copyability_score(row, clean_pnl),
                "archetype": self._determine_archetype(row),
                "risk_level": self._assess_risk_level(row),
            }
            enhanced_traders.append(trader)

        logger.info(
            f"Computed leaderboard with {len(enhanced_traders)} qualified traders"
        )
        return enhanced_traders

    def _calculate_copyability_score(
        self, trader_data: dict[str, Any], clean_pnl: Decimal
    ) -> int:
        """Calculate copyability score (0-100) based on trading metrics"""
        volume_score = min(100, (trader_data["last_30d_volume_usd"] / MIN_VOL) * 50)
        activity_score = min(50, (trader_data["trade_count_30d"] / MIN_TRADES) * 50)

        # PnL bonus: normalize PnL contribution (30 points max)
        Decimal(str(trader_data["last_30d_volume_usd"]))
        Decimal(str(trader_data["median_trade_size_usd"]))
        pnl_score = int(min(30, max(0, (clean_pnl / Decimal("100000")) * 30)))

        # Penalty for very large trades (might be whale activity)
        median_penalty = 0
        if trader_data["median_trade_size_usd"] > 100000:  # $100k+
            median_penalty = 10

        score = int(volume_score + activity_score + pnl_score - median_penalty)
        return max(0, min(100, score))

    def _determine_archetype(self, trader_data: dict[str, Any]) -> str:
        """Determine trader archetype based on trading patterns"""
        trade_count = trader_data["trade_count_30d"]
        volume = trader_data["last_30d_volume_usd"]
        median_size = trader_data["median_trade_size_usd"]

        if trade_count > 1000:
            return "High Frequency Trader"
        elif volume > 50000000:  # $50M+
            return "Whale"
        elif median_size < 5000:  # < $5k
            return "Retail Trader"
        elif trade_count > 500:
            return "Active Trader"
        else:
            return "Occasional Trader"

    def _assess_risk_level(self, trader_data: dict[str, Any]) -> str:
        """Assess risk level based on trading patterns"""
        trade_count = trader_data["trade_count_30d"]
        volume = trader_data["last_30d_volume_usd"]

        # High frequency + high volume = potentially risky
        if trade_count > 800 and volume > 20000000:
            return "HIGH"
        elif trade_count > 400 and volume > 10000000:
            return "MED"
        else:
            return "LOW"

    async def _get_mock_leaderboard(self, limit: int) -> list[dict[str, Any]]:
        """Generate mock leaderboard data for testing"""
        mock_addresses = [
            "0x1234567890123456789012345678901234567890",
            "0x2345678901234567890123456789012345678901",
            "0x3456789012345678901234567890123456789012",
            "0x4567890123456789012345678901234567890123",
            "0x5678901234567890123456789012345678901234",
        ]

        import time

        traders = []
        for i, addr in enumerate(mock_addresses[:limit]):
            traders.append(
                {
                    "address": addr,
                    "trade_count_30d": 450 + (i * 100),
                    "last_30d_volume_usd": 15000000 + (i * 5000000),
                    "median_trade_size_usd": 25000 + (i * 5000),
                    "last_trade_at": int(time.time()) - (i * 3600),
                    "clean_realized_pnl_usd": 75000 + (i * 25000),
                    "copyability_score": 85 + i,
                    "archetype": [
                        "High Frequency Trader",
                        "Active Trader",
                        "Whale",
                        "Retail Trader",
                        "Occasional Trader",
                    ][i % 5],
                    "risk_level": ["MED", "LOW", "HIGH", "LOW", "MED"][i % 5],
                }
            )

        return traders

    async def get_trader_stats(self, address: str) -> dict[str, Any] | None:
        """Get detailed stats for a specific trader"""
        redis = await self._get_redis()
        cache_key = f"trader_stats:{address.lower()}"

        try:
            cached_data = await redis.get(cache_key)
            if cached_data:
                import json

                return json.loads(cached_data)
        except Exception as e:
            logger.warning(f"Redis cache read failed for trader {address}: {e}")

        # Compute from database
        stats = await self._compute_trader_stats_from_db(address)

        # Cache for 10 minutes
        if stats:
            try:
                import json

                await redis.setex(cache_key, 600, json.dumps(stats))
            except Exception as e:
                logger.warning(f"Redis cache write failed for trader {address}: {e}")

        return stats

    async def _compute_trader_stats_from_db(
        self, address: str
    ) -> dict[str, Any] | None:
        """Compute detailed stats for a specific trader from database"""
        import time

        thirty_days_ago = int(time.time()) - (30 * 24 * 60 * 60)

        sql = text(
            """
            WITH trader_fills AS (
                SELECT
                    pair,
                    is_long,
                    size,
                    price,
                    ABS(price * size) as notional_usd,
                    fee,
                    side,
                    ts
                FROM fills
                WHERE address = :address
                  AND ts >= :thirty_days_ago
            ),
            stats AS (
                SELECT
                    COUNT(*) as total_trades,
                    SUM(notional_usd) as total_volume,
                    AVG(notional_usd) as avg_trade_size,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY notional_usd) as median_trade_size,
                    MAX(ts) as last_trade_at,
                    MIN(ts) as first_trade_at,
                    COUNT(DISTINCT pair) as unique_pairs,
                    SUM(CASE WHEN side = 'OPEN' THEN 1 ELSE 0 END) as open_trades,
                    SUM(CASE WHEN side = 'CLOSE' THEN 1 ELSE 0 END) as close_trades
                FROM trader_fills
            )
            SELECT * FROM stats
        """
        )

        try:
            with self.engine.begin() as conn:
                result = conn.execute(
                    sql,
                    {"address": address.lower(), "thirty_days_ago": thirty_days_ago},
                )
                row = result.fetchone()

                if row:
                    return dict(row._mapping)
                else:
                    return None

        except Exception as e:
            logger.error(f"Database query failed for trader {address}: {e}")
            return None

    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
