"""
Position Tracker for Vanta Bot
Calculates trader statistics using FIFO PnL methodology
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import asyncpg
import redis.asyncio as redis
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class TraderStats:
    """Trader statistics data structure"""
    address: str
    last_30d_volume_usd: float
    median_trade_size_usd: float
    trade_count_30d: int
    realized_pnl_clean_usd: float
    last_trade_at: Optional[datetime]
    maker_ratio: Optional[float]
    unique_symbols: int
    win_rate: float
    avg_hold_time_hours: float
    leverage_consistency: float

@dataclass
class PositionLot:
    """Represents a position lot for FIFO calculation"""
    size: float
    entry_price: float
    timestamp: datetime
    is_long: bool

class PositionTracker:
    """Tracks trader positions and calculates statistics using FIFO methodology"""
    
    def __init__(self, db_pool: asyncpg.Pool, redis_client: redis.Redis, config):
        self.db_pool = db_pool
        self.redis = redis_client
        self.config = config
        
    async def start_tracking(self):
        """Start background tracking of trader positions"""
        logger.info("Starting position tracking service...")
        
        while True:
            try:
                await self._update_trader_stats()
                await asyncio.sleep(60)  # Update every minute
            except Exception as e:
                logger.error(f"Error in position tracking: {e}")
                await asyncio.sleep(10)
    
    async def _update_trader_stats(self):
        """Update 30-day stats for all traders"""
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
    
    async def _get_active_traders(self, since: datetime) -> List[str]:
        """Get all unique trader addresses with activity since given time"""
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT DISTINCT address 
                    FROM trade_events 
                    WHERE timestamp >= $1
                    ORDER BY address
                """
                rows = await conn.fetch(query, since)
                return [row['address'] for row in rows]
        except Exception as e:
            logger.error(f"Error getting active traders: {e}")
            return []
    
    async def _calculate_trader_stats(self, address: str, since: datetime) -> Optional[TraderStats]:
        """Calculate comprehensive stats using FIFO PnL methodology"""
        try:
            # Get all trades for this trader since the cutoff
            trades = await self._get_trader_trades(address, since)
            
            if not trades:
                return None
            
            # Calculate FIFO realized PnL
            realized_pnl = self._calculate_fifo_pnl(trades)
            
            # Calculate volume and trade metrics
            volume = sum(trade['size'] * trade['price'] for trade in trades if trade['event_type'] == 'OPENED')
            trade_sizes = [trade['size'] * trade['price'] for trade in trades if trade['event_type'] == 'OPENED']
            median_size = self._calculate_median(trade_sizes) if trade_sizes else 0
            
            # Calculate win rate
            win_rate = self._calculate_win_rate(trades)
            
            # Calculate maker ratio (trades that add liquidity)
            maker_ratio = self._calculate_maker_ratio(trades)
            
            # Calculate unique symbols
            unique_symbols = len(set(trade['pair_symbol'] for trade in trades))
            
            # Calculate average hold time
            avg_hold_time = self._calculate_avg_hold_time(trades)
            
            # Calculate leverage consistency
            leverage_consistency = self._calculate_leverage_consistency(trades)
            
            # Get last trade timestamp
            last_trade_at = max(trade['timestamp'] for trade in trades) if trades else None
            
            return TraderStats(
                address=address,
                last_30d_volume_usd=volume,
                median_trade_size_usd=median_size,
                trade_count_30d=len([t for t in trades if t['event_type'] == 'OPENED']),
                realized_pnl_clean_usd=realized_pnl,
                last_trade_at=last_trade_at,
                maker_ratio=maker_ratio,
                unique_symbols=unique_symbols,
                win_rate=win_rate,
                avg_hold_time_hours=avg_hold_time,
                leverage_consistency=leverage_consistency
            )
            
        except Exception as e:
            logger.error(f"Error calculating stats for {address}: {e}")
            return None
    
    async def _get_trader_trades(self, address: str, since: datetime) -> List[Dict]:
        """Get all trades for a trader since given time"""
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT * FROM trade_events 
                    WHERE address = $1 AND timestamp >= $2
                    ORDER BY timestamp ASC
                """
                rows = await conn.fetch(query, address, since)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting trader trades: {e}")
            return []
    
    def _calculate_fifo_pnl(self, trades: List[Dict]) -> float:
        """Calculate realized PnL using FIFO lot matching"""
        positions = {}  # pair_symbol -> {'long': [], 'short': []}
        realized_pnl = 0.0
        
        for trade in sorted(trades, key=lambda x: x['timestamp']):
            pair_symbol = trade['pair_symbol']
            size = float(trade['size'])
            price = float(trade['price'])
            is_long = trade['is_long']
            fee = float(trade.get('fee', 0))
            
            if pair_symbol not in positions:
                positions[pair_symbol] = {'long': [], 'short': []}
            
            if trade['event_type'] == 'OPENED':
                # Opening position
                side = 'long' if is_long else 'short'
                positions[pair_symbol][side].append(PositionLot(
                    size=size,
                    entry_price=price,
                    timestamp=trade['timestamp'],
                    is_long=is_long
                ))
            
            elif trade['event_type'] == 'CLOSED':
                # Closing position - FIFO matching
                side = 'long' if is_long else 'short'
                remaining_close_size = size
                
                while remaining_close_size > 0 and positions[pair_symbol][side]:
                    lot = positions[pair_symbol][side][0]
                    
                    if remaining_close_size >= lot.size:
                        # Close entire lot
                        pnl = self._calculate_lot_pnl(lot.size, lot.entry_price, price, is_long)
                        realized_pnl += pnl - fee
                        remaining_close_size -= lot.size
                        positions[pair_symbol][side].pop(0)
                    else:
                        # Partial close
                        pnl = self._calculate_lot_pnl(remaining_close_size, lot.entry_price, price, is_long)
                        realized_pnl += pnl - fee
                        # Update remaining lot size
                        lot.size -= remaining_close_size
                        remaining_close_size = 0
        
        return realized_pnl
    
    def _calculate_lot_pnl(self, size: float, entry_price: float, exit_price: float, is_long: bool) -> float:
        """Calculate PnL for a specific lot"""
        if is_long:
            return size * (exit_price - entry_price) / entry_price
        else:
            return size * (entry_price - exit_price) / entry_price
    
    def _calculate_win_rate(self, trades: List[Dict]) -> float:
        """Calculate win rate from closed trades"""
        closed_trades = [t for t in trades if t['event_type'] == 'CLOSED']
        if not closed_trades:
            return 0.0
        
        # Group trades by pair to calculate pair-level PnL
        pair_trades = {}
        for trade in closed_trades:
            pair = trade['pair_symbol']
            if pair not in pair_trades:
                pair_trades[pair] = []
            pair_trades[pair].append(trade)
        
        winning_pairs = 0
        total_pairs = len(pair_trades)
        
        for pair, pair_trade_list in pair_trades.items():
            pair_pnl = self._calculate_fifo_pnl(pair_trade_list)
            if pair_pnl > 0:
                winning_pairs += 1
        
        return winning_pairs / total_pairs if total_pairs > 0 else 0.0
    
    def _calculate_maker_ratio(self, trades: List[Dict]) -> Optional[float]:
        """Calculate maker ratio (trades that add liquidity)"""
        # This is a simplified calculation
        # In practice, you'd need to analyze order book data
        # For now, we'll estimate based on trade frequency and size consistency
        
        if len(trades) < 10:
            return None
        
        # Calculate size consistency (more consistent = more likely to be maker)
        sizes = [t['size'] * t['price'] for t in trades if t['event_type'] == 'OPENED']
        if len(sizes) < 2:
            return None
        
        size_std = np.std(sizes)
        size_mean = np.mean(sizes)
        size_cv = size_std / size_mean if size_mean > 0 else 1.0
        
        # Lower coefficient of variation suggests more consistent sizing (maker behavior)
        maker_ratio = max(0.0, min(1.0, 1.0 - size_cv))
        
        return maker_ratio
    
    def _calculate_avg_hold_time(self, trades: List[Dict]) -> float:
        """Calculate average position hold time in hours"""
        # Group trades by pair to calculate hold times
        pair_positions = {}
        hold_times = []
        
        for trade in sorted(trades, key=lambda x: x['timestamp']):
            pair = trade['pair_symbol']
            is_long = trade['is_long']
            
            if pair not in pair_positions:
                pair_positions[pair] = {'long': [], 'short': []}
            
            side = 'long' if is_long else 'short'
            
            if trade['event_type'] == 'OPENED':
                pair_positions[pair][side].append({
                    'size': trade['size'],
                    'timestamp': trade['timestamp']
                })
            elif trade['event_type'] == 'CLOSED':
                remaining_size = trade['size']
                
                while remaining_size > 0 and pair_positions[pair][side]:
                    position = pair_positions[pair][side][0]
                    
                    if remaining_size >= position['size']:
                        # Close entire position
                        hold_time = (trade['timestamp'] - position['timestamp']).total_seconds() / 3600
                        hold_times.append(hold_time)
                        remaining_size -= position['size']
                        pair_positions[pair][side].pop(0)
                    else:
                        # Partial close
                        hold_time = (trade['timestamp'] - position['timestamp']).total_seconds() / 3600
                        hold_times.append(hold_time)
                        position['size'] -= remaining_size
                        remaining_size = 0
        
        return np.mean(hold_times) if hold_times else 0.0
    
    def _calculate_leverage_consistency(self, trades: List[Dict]) -> float:
        """Calculate leverage consistency (1.0 = very consistent, 0.0 = very inconsistent)"""
        leverages = [float(t.get('leverage', 1)) for t in trades if t['event_type'] == 'OPENED']
        
        if len(leverages) < 2:
            return 1.0
        
        leverage_std = np.std(leverages)
        leverage_mean = np.mean(leverages)
        
        if leverage_mean == 0:
            return 1.0
        
        # Coefficient of variation (lower is more consistent)
        cv = leverage_std / leverage_mean
        consistency = max(0.0, min(1.0, 1.0 - cv))
        
        return consistency
    
    def _calculate_median(self, values: List[float]) -> float:
        """Calculate median of a list of values"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        if n % 2 == 0:
            return (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
        else:
            return sorted_values[n//2]
    
    async def _cache_and_persist_stats(self, address: str, stats: TraderStats):
        """Cache and persist trader statistics"""
        try:
            # Cache in Redis for fast access
            cache_key = f"trader_stats:{address}:30d"
            await self.redis.setex(
                cache_key, 
                300,  # 5 minutes
                {
                    'address': stats.address,
                    'last_30d_volume_usd': stats.last_30d_volume_usd,
                    'median_trade_size_usd': stats.median_trade_size_usd,
                    'trade_count_30d': stats.trade_count_30d,
                    'realized_pnl_clean_usd': stats.realized_pnl_clean_usd,
                    'last_trade_at': stats.last_trade_at.isoformat() if stats.last_trade_at else None,
                    'maker_ratio': stats.maker_ratio,
                    'unique_symbols': stats.unique_symbols,
                    'win_rate': stats.win_rate,
                    'avg_hold_time_hours': stats.avg_hold_time_hours,
                    'leverage_consistency': stats.leverage_consistency,
                    'updated_at': datetime.utcnow().isoformat()
                }
            )
            
            # Persist to database
            async with self.db_pool.acquire() as conn:
                query = """
                    INSERT INTO trader_stats (
                        address, window, last_30d_volume_usd, median_trade_size_usd,
                        trade_count_30d, realized_pnl_clean_usd, last_trade_at,
                        maker_ratio, unique_symbols, win_rate, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    ON CONFLICT (address, window) DO UPDATE SET
                        last_30d_volume_usd = EXCLUDED.last_30d_volume_usd,
                        median_trade_size_usd = EXCLUDED.median_trade_size_usd,
                        trade_count_30d = EXCLUDED.trade_count_30d,
                        realized_pnl_clean_usd = EXCLUDED.realized_pnl_clean_usd,
                        last_trade_at = EXCLUDED.last_trade_at,
                        maker_ratio = EXCLUDED.maker_ratio,
                        unique_symbols = EXCLUDED.unique_symbols,
                        win_rate = EXCLUDED.win_rate,
                        updated_at = EXCLUDED.updated_at
                """
                
                await conn.execute(
                    query,
                    stats.address,
                    '30d',
                    stats.last_30d_volume_usd,
                    stats.median_trade_size_usd,
                    stats.trade_count_30d,
                    stats.realized_pnl_clean_usd,
                    stats.last_trade_at,
                    stats.maker_ratio,
                    stats.unique_symbols,
                    stats.win_rate,
                    datetime.utcnow()
                )
            
            logger.debug(f"Updated stats for trader {address[:10]}...")
            
        except Exception as e:
            logger.error(f"Error caching/persisting stats for {address}: {e}")
    
    async def get_trader_stats(self, address: str, window: str = '30d') -> Optional[TraderStats]:
        """Get cached trader statistics"""
        try:
            # Try cache first
            cache_key = f"trader_stats:{address}:{window}"
            cached_data = await self.redis.get(cache_key)
            
            if cached_data:
                data = cached_data
                return TraderStats(
                    address=data['address'],
                    last_30d_volume_usd=data['last_30d_volume_usd'],
                    median_trade_size_usd=data['median_trade_size_usd'],
                    trade_count_30d=data['trade_count_30d'],
                    realized_pnl_clean_usd=data['realized_pnl_clean_usd'],
                    last_trade_at=datetime.fromisoformat(data['last_trade_at']) if data['last_trade_at'] else None,
                    maker_ratio=data['maker_ratio'],
                    unique_symbols=data['unique_symbols'],
                    win_rate=data['win_rate'],
                    avg_hold_time_hours=data['avg_hold_time_hours'],
                    leverage_consistency=data['leverage_consistency']
                )
            
            # Fallback to database
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT * FROM trader_stats 
                    WHERE address = $1 AND window = $2
                """
                row = await conn.fetchrow(query, address, window)
                
                if row:
                    return TraderStats(
                        address=row['address'],
                        last_30d_volume_usd=float(row['last_30d_volume_usd']),
                        median_trade_size_usd=float(row['median_trade_size_usd']),
                        trade_count_30d=row['trade_count_30d'],
                        realized_pnl_clean_usd=float(row['realized_pnl_clean_usd']),
                        last_trade_at=row['last_trade_at'],
                        maker_ratio=float(row['maker_ratio']) if row['maker_ratio'] else None,
                        unique_symbols=row['unique_symbols'],
                        win_rate=float(row['win_rate']),
                        avg_hold_time_hours=0.0,  # Not stored in DB yet
                        leverage_consistency=0.0  # Not stored in DB yet
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting trader stats for {address}: {e}")
            return None
    
    async def get_top_traders_by_volume(self, limit: int = 100) -> List[TraderStats]:
        """Get top traders by volume"""
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT * FROM trader_stats 
                    WHERE window = '30d' 
                    ORDER BY last_30d_volume_usd DESC 
                    LIMIT $1
                """
                rows = await conn.fetch(query, limit)
                
                return [
                    TraderStats(
                        address=row['address'],
                        last_30d_volume_usd=float(row['last_30d_volume_usd']),
                        median_trade_size_usd=float(row['median_trade_size_usd']),
                        trade_count_30d=row['trade_count_30d'],
                        realized_pnl_clean_usd=float(row['realized_pnl_clean_usd']),
                        last_trade_at=row['last_trade_at'],
                        maker_ratio=float(row['maker_ratio']) if row['maker_ratio'] else None,
                        unique_symbols=row['unique_symbols'],
                        win_rate=float(row['win_rate']),
                        avg_hold_time_hours=0.0,
                        leverage_consistency=0.0
                    )
                    for row in rows
                ]
                
        except Exception as e:
            logger.error(f"Error getting top traders: {e}")
            return []
    
    async def stop(self):
        """Stop the position tracker"""
        logger.info("Stopping position tracker...")
        # Cleanup resources if needed
