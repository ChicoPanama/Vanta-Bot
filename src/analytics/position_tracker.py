"""
Position Tracker for Vanta Bot
Handles real-time position tracking and FIFO PnL calculation
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from statistics import median

import asyncpg
import redis.asyncio as redis
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class TraderStats:
    address: str
    last_30d_volume_usd: float
    median_trade_size_usd: float
    trade_count_30d: int
    realized_pnl_clean_usd: float
    last_trade_at: Optional[datetime]
    maker_ratio: Optional[float]
    unique_symbols: int
    win_rate: float

@dataclass
class Position:
    size: float
    entry_price: float
    timestamp: datetime
    leverage: int

class PositionTracker:
    """Tracks trader positions and calculates FIFO PnL"""
    
    def __init__(self, db_pool: asyncpg.Pool, redis_client: redis.Redis, config):
        self.db_pool = db_pool
        self.redis = redis_client
        self.config = config
        self.is_running = False
        
    async def start_tracking(self):
        """Start background tracking of trader positions"""
        if self.is_running:
            logger.warning("Position tracker is already running")
            return
            
        self.is_running = True
        logger.info("Starting position tracking...")
        
        try:
            while self.is_running:
                await self._update_trader_stats()
                await asyncio.sleep(60)  # Update every minute
                
        except Exception as e:
            logger.error(f"Error in position tracking: {e}")
            self.is_running = False
            raise
    
    async def stop_tracking(self):
        """Stop position tracking"""
        self.is_running = False
        logger.info("Stopped position tracking")
    
    async def _update_trader_stats(self):
        """Update 30-day stats for all traders"""
        try:
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            # Get all unique traders with activity in last 30 days
            active_traders = await self._get_active_traders(thirty_days_ago)
            
            logger.info(f"Updating stats for {len(active_traders)} active traders")
            
            for trader_address in active_traders:
                try:
                    stats = await self._calculate_trader_stats(trader_address, thirty_days_ago)
                    if stats:
                        await self._cache_and_persist_stats(trader_address, stats)
                except Exception as e:
                    logger.error(f"Error calculating stats for {trader_address}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in _update_trader_stats: {e}")
    
    async def _get_active_traders(self, since: datetime) -> List[str]:
        """Get list of traders with activity since given time"""
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT DISTINCT address
                    FROM trade_events
                    WHERE timestamp >= $1
                    ORDER BY address
                """, since)
                
                return [row['address'] for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting active traders: {e}")
            return []
    
    async def _calculate_trader_stats(self, address: str, since: datetime) -> Optional[TraderStats]:
        """Calculate comprehensive stats using FIFO PnL methodology"""
        try:
            # Get all trades for this trader
            trades = await self._get_trader_trades(address, since)
            
            if not trades:
                return None
            
            # FIFO lot matching for realized PnL
            realized_pnl = self._calculate_fifo_pnl(trades)
            
            # Volume and trade metrics
            volume = sum(trade['size'] * trade['price'] for trade in trades)
            trade_sizes = [trade['size'] * trade['price'] for trade in trades]
            median_size = median(trade_sizes) if trade_sizes else 0
            
            # Win rate calculation
            closed_trades = [t for t in trades if t['event_type'] == 'CLOSED']
            winning_trades = [t for t in closed_trades if t.get('pnl', 0) > 0]
            win_rate = len(winning_trades) / len(closed_trades) if closed_trades else 0
            
            # Maker ratio (trades that add liquidity)
            maker_ratio = self._calculate_maker_ratio(trades)
            
            # Unique symbols
            unique_symbols = len(set(trade['pair'] for trade in trades))
            
            # Last trade time
            last_trade_at = max(trade['timestamp'] for trade in trades) if trades else None
            
            return TraderStats(
                address=address,
                last_30d_volume_usd=volume,
                median_trade_size_usd=median_size,
                trade_count_30d=len(trades),
                realized_pnl_clean_usd=realized_pnl,
                last_trade_at=last_trade_at,
                maker_ratio=maker_ratio,
                unique_symbols=unique_symbols,
                win_rate=win_rate
            )
            
        except Exception as e:
            logger.error(f"Error calculating trader stats for {address}: {e}")
            return None
    
    async def _get_trader_trades(self, address: str, since: datetime) -> List[Dict]:
        """Get trades for a trader since given time"""
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT pair, is_long, size, price, leverage, event_type, 
                           timestamp, fee, block_number, tx_hash
                    FROM trade_events
                    WHERE address = $1 AND timestamp >= $2
                    ORDER BY timestamp ASC
                """, address, since)
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting trades for {address}: {e}")
            return []
    
    def _calculate_fifo_pnl(self, trades: List[Dict]) -> float:
        """Calculate realized PnL using FIFO lot matching"""
        positions = {}  # pair -> {'long': [], 'short': []}
        realized_pnl = 0.0
        
        for trade in sorted(trades, key=lambda x: x['timestamp']):
            pair = trade['pair']
            size = trade['size']
            price = trade['price']
            is_long = trade['is_long']
            
            if pair not in positions:
                positions[pair] = {'long': [], 'short': []}
            
            if trade['event_type'] == 'OPENED':
                # Opening position
                side = 'long' if is_long else 'short'
                positions[pair][side].append(Position(
                    size=size,
                    entry_price=price,
                    timestamp=trade['timestamp'],
                    leverage=trade['leverage']
                ))
            
            elif trade['event_type'] == 'CLOSED':
                # Closing position - FIFO matching
                side = 'long' if is_long else 'short'
                remaining_close_size = size
                
                while remaining_close_size > 0 and positions[pair][side]:
                    open_position = positions[pair][side][0]
                    
                    if remaining_close_size >= open_position.size:
                        # Close entire lot
                        pnl = self._calculate_lot_pnl(
                            open_position.size, 
                            open_position.entry_price, 
                            price, 
                            is_long
                        )
                        realized_pnl += pnl - trade.get('fee', 0)
                        remaining_close_size -= open_position.size
                        positions[pair][side].pop(0)
                    else:
                        # Partial close
                        pnl = self._calculate_lot_pnl(
                            remaining_close_size, 
                            open_position.entry_price, 
                            price, 
                            is_long
                        )
                        realized_pnl += pnl - trade.get('fee', 0)
                        # Update remaining lot size
                        positions[pair][side][0] = Position(
                            size=open_position.size - remaining_close_size,
                            entry_price=open_position.entry_price,
                            timestamp=open_position.timestamp,
                            leverage=open_position.leverage
                        )
                        remaining_close_size = 0
        
        return realized_pnl
    
    def _calculate_lot_pnl(self, size: float, entry_price: float, exit_price: float, is_long: bool) -> float:
        """Calculate PnL for a specific lot"""
        if entry_price == 0:
            return 0.0
            
        if is_long:
            return size * (exit_price - entry_price) / entry_price
        else:
            return size * (entry_price - exit_price) / entry_price
    
    def _calculate_maker_ratio(self, trades: List[Dict]) -> Optional[float]:
        """Calculate maker ratio (trades that add liquidity)"""
        # This is a simplified calculation
        # In practice, you'd need to analyze if trades crossed the spread
        # For now, return None to indicate unknown
        return None
    
    async def _cache_and_persist_stats(self, address: str, stats: TraderStats):
        """Cache and persist trader stats"""
        try:
            # Cache in Redis for fast access
            cache_key = f"trader_stats:{address}:30d"
            await self.redis.hset(cache_key, mapping={
                'volume': stats.last_30d_volume_usd,
                'median_size': stats.median_trade_size_usd,
                'trade_count': stats.trade_count_30d,
                'realized_pnl': stats.realized_pnl_clean_usd,
                'win_rate': stats.win_rate,
                'unique_symbols': stats.unique_symbols,
                'updated_at': datetime.utcnow().isoformat()
            })
            await self.redis.expire(cache_key, 3600)  # Cache for 1 hour
            
            # Persist to database
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO trader_stats (
                        address, window, last_30d_volume_usd, median_trade_size_usd,
                        trade_count_30d, realized_pnl_clean_usd, last_trade_at,
                        maker_ratio, unique_symbols, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (address, window) DO UPDATE SET
                        last_30d_volume_usd = EXCLUDED.last_30d_volume_usd,
                        median_trade_size_usd = EXCLUDED.median_trade_size_usd,
                        trade_count_30d = EXCLUDED.trade_count_30d,
                        realized_pnl_clean_usd = EXCLUDED.realized_pnl_clean_usd,
                        last_trade_at = EXCLUDED.last_trade_at,
                        maker_ratio = EXCLUDED.maker_ratio,
                        unique_symbols = EXCLUDED.unique_symbols,
                        updated_at = EXCLUDED.updated_at
                """, 
                    address,
                    '30d',
                    stats.last_30d_volume_usd,
                    stats.median_trade_size_usd,
                    stats.trade_count_30d,
                    stats.realized_pnl_clean_usd,
                    stats.last_trade_at,
                    stats.maker_ratio,
                    stats.unique_symbols,
                    datetime.utcnow()
                )
                
        except Exception as e:
            logger.error(f"Error caching/persisting stats for {address}: {e}")
    
    async def get_trader_stats(self, address: str, window: str = '30d') -> Optional[TraderStats]:
        """Get cached trader stats"""
        try:
            # Try cache first
            cache_key = f"trader_stats:{address}:{window}"
            cached_data = await self.redis.hgetall(cache_key)
            
            if cached_data:
                return TraderStats(
                    address=address,
                    last_30d_volume_usd=float(cached_data.get('volume', 0)),
                    median_trade_size_usd=float(cached_data.get('median_size', 0)),
                    trade_count_30d=int(cached_data.get('trade_count', 0)),
                    realized_pnl_clean_usd=float(cached_data.get('realized_pnl', 0)),
                    last_trade_at=None,  # Not cached
                    maker_ratio=None,    # Not cached
                    unique_symbols=int(cached_data.get('unique_symbols', 0)),
                    win_rate=float(cached_data.get('win_rate', 0))
                )
            
            # Fallback to database
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT * FROM trader_stats
                    WHERE address = $1 AND window = $2
                """, address, window)
                
                if row:
                    return TraderStats(
                        address=row['address'],
                        last_30d_volume_usd=float(row['last_30d_volume_usd'] or 0),
                        median_trade_size_usd=float(row['median_trade_size_usd'] or 0),
                        trade_count_30d=int(row['trade_count_30d'] or 0),
                        realized_pnl_clean_usd=float(row['realized_pnl_clean_usd'] or 0),
                        last_trade_at=row['last_trade_at'],
                        maker_ratio=float(row['maker_ratio']) if row['maker_ratio'] else None,
                        unique_symbols=int(row['unique_symbols'] or 0),
                        win_rate=0.0  # Would need to calculate from trades
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting trader stats for {address}: {e}")
            return None
    
    async def get_top_traders_by_volume(self, limit: int = 100) -> List[TraderStats]:
        """Get top traders by volume"""
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT * FROM trader_stats
                    WHERE window = '30d' AND last_trade_at > NOW() - INTERVAL '72 hours'
                    ORDER BY last_30d_volume_usd DESC
                    LIMIT $1
                """, limit)
                
                return [
                    TraderStats(
                        address=row['address'],
                        last_30d_volume_usd=float(row['last_30d_volume_usd'] or 0),
                        median_trade_size_usd=float(row['median_trade_size_usd'] or 0),
                        trade_count_30d=int(row['trade_count_30d'] or 0),
                        realized_pnl_clean_usd=float(row['realized_pnl_clean_usd'] or 0),
                        last_trade_at=row['last_trade_at'],
                        maker_ratio=float(row['maker_ratio']) if row['maker_ratio'] else None,
                        unique_symbols=int(row['unique_symbols'] or 0),
                        win_rate=0.0
                    ) for row in rows
                ]
                
        except Exception as e:
            logger.error(f"Error getting top traders: {e}")
            return []