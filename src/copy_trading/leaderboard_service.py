"""
Leaderboard Service for Vanta Bot
Manages trader rankings and copyability scores
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import numpy as np
import asyncpg
import redis.asyncio as redis

from ..analytics.position_tracker import TraderStats
from ..ai.trader_analyzer import TraderAnalyzer

logger = logging.getLogger(__name__)

@dataclass
class TraderRanking:
    """Trader ranking data structure"""
    address: str
    ranking_score: float
    volume_rank: int
    pnl_rank: int
    copyability_score: int
    archetype: str
    risk_level: str
    last_30d_volume_usd: float
    realized_pnl_clean_usd: float
    trade_count_30d: int
    win_rate: float
    sharpe_like: float
    consistency: float
    last_trade_at: datetime

class LeaderboardService:
    """Service for managing trader leaderboards and rankings"""
    
    def __init__(self, db_pool: asyncpg.Pool, redis_client: redis.Redis, 
                 trader_analyzer: TraderAnalyzer, config):
        self.db_pool = db_pool
        self.redis = redis_client
        self.analyzer = trader_analyzer
        self.config = config
        
    async def get_top_traders(self, limit: int = 50, window: str = '30d') -> List[Dict]:
        """Get ranked list of top traders with AI scoring"""
        try:
            # Check cache first
            cache_key = f"leaderboard:{window}:{limit}"
            cached = await self.redis.get(cache_key)
            
            if cached:
                return json.loads(cached)
            
            # Fetch from database with filters
            traders = await self._fetch_filtered_traders(window)
            
            # Apply ranking algorithm
            ranked_traders = await self._rank_traders(traders)
            
            # Add AI analysis
            enriched_traders = await self._enrich_with_ai_analysis(ranked_traders)
            
            # Take top N
            top_traders = enriched_traders[:limit]
            
            # Cache for 5 minutes
            await self.redis.setex(cache_key, 300, json.dumps(top_traders, default=str))
            
            return top_traders
            
        except Exception as e:
            logger.error(f"Error getting top traders: {e}")
            return []
    
    async def _fetch_filtered_traders(self, window: str) -> List[Dict]:
        """Fetch traders that meet quality criteria"""
        try:
            query = """
                SELECT 
                    ts.address,
                    ts.last_30d_volume_usd,
                    ts.median_trade_size_usd,
                    ts.trade_count_30d,
                    ts.realized_pnl_clean_usd,
                    ts.last_trade_at,
                    ts.maker_ratio,
                    ts.unique_symbols,
                    ts.win_rate,
                    ta.archetype,
                    ta.risk_level,
                    ta.sharpe_like,
                    ta.consistency
                FROM trader_stats ts
                LEFT JOIN trader_analytics ta ON ts.address = ta.address AND ts.window = ta.window
                WHERE ts.window = $1
                  AND ts.last_trade_at > NOW() - INTERVAL '%s hours'
                  AND ts.trade_count_30d >= $2
                  AND ts.last_30d_volume_usd >= $3
                  AND (ts.maker_ratio IS NULL OR ts.maker_ratio <= 0.95)
                  AND ts.unique_symbols >= 3
                ORDER BY ts.last_30d_volume_usd DESC
            """ % self.config.LEADER_ACTIVE_HOURS
            
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(
                    query, 
                    window,
                    self.config.LEADER_MIN_TRADES_30D,
                    self.config.LEADER_MIN_VOLUME_30D_USD
                )
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error fetching filtered traders: {e}")
            return []
    
    async def _rank_traders(self, traders: List[Dict]) -> List[Dict]:
        """Apply multi-factor ranking algorithm"""
        try:
            for trader in traders:
                # Primary ranking factors
                volume_score = np.log1p(trader['last_30d_volume_usd']) / 20  # Normalize
                pnl_score = max(0, trader['realized_pnl_clean_usd']) / max(trader['last_30d_volume_usd'], 1)
                consistency_score = trader.get('consistency', 0.5) or 0.5
                recency_score = self._calculate_recency_score(trader['last_trade_at'])
                
                # Composite score
                trader['ranking_score'] = (
                    volume_score * 0.4 +
                    pnl_score * 0.3 +
                    consistency_score * 0.2 +
                    recency_score * 0.1
                )
            
            # Sort by composite score
            return sorted(traders, key=lambda x: x['ranking_score'], reverse=True)
            
        except Exception as e:
            logger.error(f"Error ranking traders: {e}")
            return traders
    
    def _calculate_recency_score(self, last_trade_at: datetime) -> float:
        """Calculate recency score based on last trade time"""
        if not last_trade_at:
            return 0.0
        
        hours_since_last_trade = (datetime.utcnow() - last_trade_at).total_seconds() / 3600
        
        # Score decreases with time since last trade
        if hours_since_last_trade <= 24:
            return 1.0
        elif hours_since_last_trade <= 72:
            return 0.8
        elif hours_since_last_trade <= 168:  # 1 week
            return 0.6
        elif hours_since_last_trade <= 336:  # 2 weeks
            return 0.4
        else:
            return 0.2
    
    async def _enrich_with_ai_analysis(self, traders: List[Dict]) -> List[Dict]:
        """Add AI analysis and copyability scores"""
        try:
            for trader in traders:
                # Get AI analysis if available
                ai_analysis = await self._get_ai_analysis(trader['address'])
                
                if ai_analysis:
                    trader.update(ai_analysis)
                    
                    # Calculate copyability score (0-100)
                    copyability = self._calculate_copyability_score(trader)
                    trader['copyability_score'] = copyability
                else:
                    trader['copyability_score'] = 50  # Neutral score
            
            return traders
            
        except Exception as e:
            logger.error(f"Error enriching with AI analysis: {e}")
            return traders
    
    async def _get_ai_analysis(self, address: str) -> Optional[Dict]:
        """Get AI analysis for a trader"""
        try:
            # Check cache first
            cache_key = f"ai_analysis:{address}"
            cached = await self.redis.get(cache_key)
            
            if cached:
                return json.loads(cached)
            
            # Get from database
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT * FROM trader_analytics 
                    WHERE address = $1 AND window = '30d'
                """
                row = await conn.fetchrow(query, address)
                
                if row:
                    analysis = {
                        'archetype': row['archetype'],
                        'risk_level': row['risk_level'],
                        'sharpe_like': float(row['sharpe_like']),
                        'max_drawdown': float(row['max_drawdown']),
                        'consistency': float(row['consistency']),
                        'win_prob_7d': float(row['win_prob_7d']),
                        'expected_dd_7d': float(row['expected_dd_7d']),
                        'optimal_copy_ratio': float(row['optimal_copy_ratio']),
                        'strengths': row['strengths'] or [],
                        'warnings': row['warnings'] or []
                    }
                    
                    # Cache for 1 hour
                    await self.redis.setex(cache_key, 3600, json.dumps(analysis))
                    
                    return analysis
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting AI analysis for {address}: {e}")
            return None
    
    def _calculate_copyability_score(self, trader: Dict) -> int:
        """Calculate 0-100 copyability score combining stats and AI analysis"""
        try:
            base_score = 50
            
            # Volume factor (higher volume = easier to copy)
            volume_factor = min(20, np.log1p(trader['last_30d_volume_usd']) / 2)
            
            # Consistency factor
            consistency = trader.get('consistency', 0.5) or 0.5
            consistency_factor = consistency * 15
            
            # Risk factor (medium risk preferred for copying)
            risk_level = trader.get('risk_level', 'MED')
            risk_factor = {'LOW': 5, 'MED': 15, 'HIGH': -10}.get(risk_level, 0)
            
            # Win rate factor
            win_rate = trader.get('win_rate', 0.5) or 0.5
            win_rate_factor = (win_rate - 0.5) * 20
            
            # Archetype factor (some archetypes copy better)
            archetype = trader.get('archetype', 'Unknown')
            archetype_factor = {
                'Conservative Scalper': 10,
                'Risk Manager': 15,
                'Precision Trader': 12,
                'Volume Hunter': 5,
                'Aggressive Swinger': -5
            }.get(archetype, 0)
            
            # Sharpe ratio factor
            sharpe_like = trader.get('sharpe_like', 0) or 0
            sharpe_factor = min(10, max(-10, sharpe_like * 5))
            
            # Trade count factor (more trades = more data)
            trade_count = trader.get('trade_count_30d', 0)
            trade_count_factor = min(10, trade_count / 100)
            
            total_score = (base_score + volume_factor + consistency_factor + 
                          risk_factor + win_rate_factor + archetype_factor + 
                          sharpe_factor + trade_count_factor)
            
            return max(0, min(100, int(total_score)))
            
        except Exception as e:
            logger.error(f"Error calculating copyability score: {e}")
            return 50
    
    async def get_trader_card(self, address: str) -> Optional[Dict]:
        """Get detailed trader profile for UI display"""
        try:
            # Get basic stats
            stats = await self._get_trader_stats(address)
            if not stats:
                return None
            
            # Get AI analysis
            ai_analysis = await self._get_ai_analysis(address)
            
            # Get recent performance
            recent_trades = await self._get_recent_trades(address, limit=10)
            
            # Calculate additional metrics
            card_data = {
                **stats,
                **ai_analysis,
                'recent_trades': recent_trades,
                'copyability_score': self._calculate_copyability_score({**stats, **ai_analysis}),
                'strengths': ai_analysis.get('strengths', []) if ai_analysis else [],
                'warnings': ai_analysis.get('warnings', []) if ai_analysis else [],
                'optimal_copy_size': self._suggest_copy_size(stats, ai_analysis)
            }
            
            return card_data
            
        except Exception as e:
            logger.error(f"Error getting trader card for {address}: {e}")
            return None
    
    async def _get_trader_stats(self, address: str) -> Optional[Dict]:
        """Get trader statistics"""
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT * FROM trader_stats 
                    WHERE address = $1 AND window = '30d'
                """
                row = await conn.fetchrow(query, address)
                
                if row:
                    return {
                        'address': row['address'],
                        'last_30d_volume_usd': float(row['last_30d_volume_usd']),
                        'median_trade_size_usd': float(row['median_trade_size_usd']),
                        'trade_count_30d': row['trade_count_30d'],
                        'realized_pnl_clean_usd': float(row['realized_pnl_clean_usd']),
                        'last_trade_at': row['last_trade_at'],
                        'maker_ratio': float(row['maker_ratio']) if row['maker_ratio'] else None,
                        'unique_symbols': row['unique_symbols'],
                        'win_rate': float(row['win_rate'])
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting trader stats for {address}: {e}")
            return None
    
    async def _get_recent_trades(self, address: str, limit: int = 10) -> List[Dict]:
        """Get recent trades for a trader"""
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT * FROM trade_events 
                    WHERE address = $1 
                    ORDER BY timestamp DESC 
                    LIMIT $2
                """
                rows = await conn.fetch(query, address, limit)
                
                return [
                    {
                        'pair_symbol': row['pair_symbol'],
                        'is_long': row['is_long'],
                        'size': float(row['size']),
                        'price': float(row['price']),
                        'leverage': float(row['leverage']),
                        'event_type': row['event_type'],
                        'timestamp': row['timestamp'],
                        'tx_hash': row['tx_hash']
                    }
                    for row in rows
                ]
                
        except Exception as e:
            logger.error(f"Error getting recent trades for {address}: {e}")
            return []
    
    def _suggest_copy_size(self, stats: Dict, ai_analysis: Optional[Dict]) -> float:
        """Suggest optimal copy size for a trader"""
        try:
            if not ai_analysis:
                return 100.0  # Default suggestion
            
            # Base suggestion on optimal copy ratio
            optimal_ratio = ai_analysis.get('optimal_copy_ratio', 0.1)
            
            # Adjust based on trader volume
            volume = stats.get('last_30d_volume_usd', 0)
            if volume > 1000000:  # > $1M volume
                base_size = 1000
            elif volume > 100000:  # > $100K volume
                base_size = 500
            else:
                base_size = 100
            
            # Apply optimal ratio
            suggested_size = base_size * optimal_ratio
            
            return max(50, min(5000, suggested_size))  # Clamp to reasonable range
            
        except Exception as e:
            logger.error(f"Error suggesting copy size: {e}")
            return 100.0
    
    async def get_trader_rankings(self, address: str) -> Optional[Dict]:
        """Get ranking information for a specific trader"""
        try:
            # Get all traders for ranking
            all_traders = await self._fetch_filtered_traders('30d')
            ranked_traders = await self._rank_traders(all_traders)
            
            # Find the trader
            trader_rank = None
            for i, trader in enumerate(ranked_traders):
                if trader['address'] == address:
                    trader_rank = {
                        'overall_rank': i + 1,
                        'total_traders': len(ranked_traders),
                        'ranking_score': trader['ranking_score'],
                        'percentile': (1 - (i + 1) / len(ranked_traders)) * 100
                    }
                    break
            
            return trader_rank
            
        except Exception as e:
            logger.error(f"Error getting trader rankings for {address}: {e}")
            return None
    
    async def get_leaderboard_stats(self) -> Dict[str, Any]:
        """Get overall leaderboard statistics"""
        try:
            # Get all traders
            all_traders = await self._fetch_filtered_traders('30d')
            
            if not all_traders:
                return {
                    'total_traders': 0,
                    'total_volume': 0,
                    'total_pnl': 0,
                    'avg_win_rate': 0,
                    'top_archetype': 'Unknown'
                }
            
            # Calculate statistics
            total_volume = sum(t['last_30d_volume_usd'] for t in all_traders)
            total_pnl = sum(t['realized_pnl_clean_usd'] for t in all_traders)
            avg_win_rate = np.mean([t['win_rate'] for t in all_traders])
            
            # Most common archetype
            archetypes = [t.get('archetype', 'Unknown') for t in all_traders if t.get('archetype')]
            if archetypes:
                from collections import Counter
                archetype_counts = Counter(archetypes)
                top_archetype = archetype_counts.most_common(1)[0][0]
            else:
                top_archetype = 'Unknown'
            
            return {
                'total_traders': len(all_traders),
                'total_volume': total_volume,
                'total_pnl': total_pnl,
                'avg_win_rate': avg_win_rate,
                'top_archetype': top_archetype,
                'avg_trade_count': np.mean([t['trade_count_30d'] for t in all_traders]),
                'avg_consistency': np.mean([t.get('consistency', 0.5) or 0.5 for t in all_traders])
            }
            
        except Exception as e:
            logger.error(f"Error getting leaderboard stats: {e}")
            return {
                'total_traders': 0,
                'total_volume': 0,
                'total_pnl': 0,
                'avg_win_rate': 0,
                'top_archetype': 'Unknown'
            }
    
    async def search_traders(self, query: str, limit: int = 20) -> List[Dict]:
        """Search traders by address or other criteria"""
        try:
            # For now, we'll search by address prefix
            # In the future, this could be expanded to search by archetype, etc.
            
            async with self.db_pool.acquire() as conn:
                search_query = """
                    SELECT ts.*, ta.archetype, ta.risk_level
                    FROM trader_stats ts
                    LEFT JOIN trader_analytics ta ON ts.address = ta.address AND ts.window = ta.window
                    WHERE ts.address ILIKE $1
                      AND ts.trade_count_30d >= 20
                    ORDER BY ts.last_30d_volume_usd DESC
                    LIMIT $2
                """
                
                rows = await conn.fetch(search_query, f"{query}%", limit)
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error searching traders: {e}")
            return []
    
    async def get_trending_traders(self, hours: int = 24, limit: int = 10) -> List[Dict]:
        """Get trending traders (recently active with good performance)"""
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT 
                        ts.*,
                        ta.archetype,
                        ta.risk_level,
                        ta.copyability_score,
                        COUNT(te.id) as recent_trades
                    FROM trader_stats ts
                    LEFT JOIN trader_analytics ta ON ts.address = ta.address AND ts.window = ta.window
                    LEFT JOIN trade_events te ON ts.address = te.address 
                        AND te.timestamp > NOW() - INTERVAL '%s hours'
                    WHERE ts.last_trade_at > NOW() - INTERVAL '%s hours'
                      AND ts.trade_count_30d >= 50
                      AND ts.realized_pnl_clean_usd > 0
                    GROUP BY ts.address, ta.archetype, ta.risk_level, ta.copyability_score
                    ORDER BY recent_trades DESC, ts.realized_pnl_clean_usd DESC
                    LIMIT $1
                """ % (hours, hours)
                
                rows = await conn.fetch(query, limit)
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting trending traders: {e}")
            return []
    
    async def get_top_performers_by_archetype(self, limit: int = 5) -> Dict[str, List[Dict]]:
        """Get top performers grouped by archetype"""
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT 
                        ts.*,
                        ta.archetype,
                        ta.risk_level,
                        ta.copyability_score,
                        ROW_NUMBER() OVER (PARTITION BY ta.archetype ORDER BY ts.realized_pnl_clean_usd DESC) as rank
                    FROM trader_stats ts
                    LEFT JOIN trader_analytics ta ON ts.address = ta.address AND ts.window = ta.window
                    WHERE ta.archetype IS NOT NULL
                      AND ts.trade_count_30d >= 50
                      AND ts.last_trade_at > NOW() - INTERVAL '7 days'
                """
                
                rows = await conn.fetch(query)
                
                # Group by archetype
                archetype_groups = {}
                for row in rows:
                    archetype = row['archetype']
                    if archetype not in archetype_groups:
                        archetype_groups[archetype] = []
                    
                    if row['rank'] <= limit:
                        archetype_groups[archetype].append(dict(row))
                
                return archetype_groups
                
        except Exception as e:
            logger.error(f"Error getting top performers by archetype: {e}")
            return {}
    
    async def stop(self):
        """Stop the leaderboard service"""
        logger.info("Stopping leaderboard service...")
        # Cleanup resources if needed
