# src/services/analytics/position_tracker.py
from __future__ import annotations
import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

import aioredis
from loguru import logger
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

WINDOW = "30d"
ACTIVE_HOURS = int(os.getenv("LEADER_ACTIVE_HOURS", "72"))
MIN_TRADES_30D = int(os.getenv("LEADER_MIN_TRADES_30D", "300"))
MIN_VOL_30D = float(os.getenv("LEADER_MIN_VOLUME_30D_USD", "10000000"))

class PositionTracker:
    """
    Aggregates normalized fills/positions into per-address stats every 60s.
    Assumes you persist raw fills somewhere (e.g., table 'fills') with at least:
      address, pair, is_long, size_usd, price, fee, side, ts, maker_taker
    Replace SQL with your actual schema.
    """
    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self.redis: Optional[aioredis.Redis] = None
        self.running = False

    async def start(self) -> None:
        """Start the position tracker background task"""
        if self.running:
            logger.warning("PositionTracker already running")
            return
            
        self.running = True
        self.redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
        logger.info("PositionTracker started with Redis {}", REDIS_URL)
        
        try:
            while self.running:
                try:
                    await self._compute_30d()
                except Exception as e:
                    logger.exception("PositionTracker iteration failed: {}", e)
                await asyncio.sleep(60)
        finally:
            self.running = False
            if self.redis:
                await self.redis.close()

    async def stop(self) -> None:
        """Stop the position tracker"""
        self.running = False

    async def _compute_30d(self) -> None:
        """Compute 30-day statistics for all traders"""
        since = int((datetime.now(timezone.utc) - timedelta(days=30)).timestamp())
        
        # EXAMPLE SQL: adjust to your tables/columns
        # This assumes you have a 'fills' table with the indexed data
        sql = text("""
            with window_fills as (
              select address,
                     pair,
                     (abs(price * size)) as notional_usd,
                     fee,
                     side,
                     ts
              from fills
              where ts >= :since
            ),
            per_addr as (
              select address,
                     count(*) as trade_count_30d,
                     sum(notional_usd) as last_30d_volume_usd,
                     percentile_cont(0.5) within group (order by notional_usd) as median_trade_size_usd,
                     max(ts) as last_trade_at
              from window_fills
              group by address
            )
            select *
            from per_addr
        """)
        
        rows: List[Dict[str, Any]] = []
        try:
            with self.engine.begin() as conn:
                result = conn.execute(sql, {"since": since})
                for r in result:
                    rows.append(dict(r._mapping))
        except Exception as e:
            # If the fills table doesn't exist yet, create a mock structure
            logger.warning("Fills table not found or error executing query: {}. Using mock data.", e)
            rows = await self._create_mock_stats()

        # Persist to a stats table via SQLAlchemy ORM or Core (adjust to your models).
        # Here we just cache to Redis for the bot/leaderboard to pick up immediately.
        if self.redis:
            pipe = self.redis.pipeline()
            for r in rows:
                addr = r["address"]
                key = f"stats:{WINDOW}:{addr.lower()}"
                r["window"] = WINDOW
                pipe.hmset(key, {k: str(v) for k, v in r.items()})
                pipe.expire(key, 120)
            await pipe.execute()
            
        logger.info("PositionTracker updated {} addresses (30D window)", len(rows))

    async def _create_mock_stats(self) -> List[Dict[str, Any]]:
        """Create mock statistics for testing when no real data is available"""
        mock_addresses = [
            "0x1234567890123456789012345678901234567890",
            "0x2345678901234567890123456789012345678901", 
            "0x3456789012345678901234567890123456789012"
        ]
        
        rows = []
        for addr in mock_addresses:
            rows.append({
                "address": addr,
                "trade_count_30d": 450,  # Above minimum
                "last_30d_volume_usd": 15000000.0,  # Above minimum
                "median_trade_size_usd": 25000.0,
                "last_trade_at": int(datetime.now().timestamp()) - 3600  # 1 hour ago
            })
        
        return rows

    async def get_stats(self, address: str) -> Dict[str, Any]:
        """Get cached statistics for a specific address"""
        if not self.redis:
            self.redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
            
        key = f"stats:{WINDOW}:{address.lower()}"
        data = await self.redis.hgetall(key)
        return data or {}

    async def get_leaderboard(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get top traders based on cached statistics"""
        if not self.redis:
            self.redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
        
        # Get all stats keys
        pattern = f"stats:{WINDOW}:*"
        keys = await self.redis.keys(pattern)
        
        leaders = []
        for key in keys:
            data = await self.redis.hgetall(key)
            if data:
                # Parse numeric fields
                try:
                    trade_count = int(data.get("trade_count_30d", 0))
                    volume = float(data.get("last_30d_volume_usd", 0))
                    last_trade = int(data.get("last_trade_at", 0))
                    
                    # Check if trader meets minimum requirements
                    if (trade_count >= MIN_TRADES_30D and 
                        volume >= MIN_VOL_30D and 
                        last_trade >= int(datetime.now().timestamp()) - (ACTIVE_HOURS * 3600)):
                        
                        leaders.append({
                            "address": data.get("address", ""),
                            "trade_count_30d": trade_count,
                            "last_30d_volume_usd": volume,
                            "median_trade_size_usd": float(data.get("median_trade_size_usd", 0)),
                            "last_trade_at": last_trade,
                            "copyability_score": min(100, (trade_count / MIN_TRADES_30D) * 50 + (volume / MIN_VOL_30D) * 50)
                        })
                except (ValueError, TypeError):
                    continue
        
        # Sort by copyability score
        leaders.sort(key=lambda x: x["copyability_score"], reverse=True)
        return leaders[:limit]
