"""
Leaderboard Service for Vanta Bot
Ranks traders based on performance and AI analysis
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

import asyncpg
import redis.asyncio as redis
import numpy as np

from ..analytics.position_tracker import TraderStats
from ..ai.trader_analyzer import TraderAnalyzer

logger = logging.getLogger(__name__)

@dataclass
class TraderRanking:
    address: str
    ranking_score: float
    copyability_score: int
    volume_score: float
    pnl_score: float
    consistency_score: float
    recency_score: float
    archetype: str
    risk_level: str
    ai_analysis: Optional[Dict]

class LeaderboardService:
    """Service for ranking and managing trader leaderboards"""
    
    def __init__(self, db_pool: asyncpg.Pool, redis_client: redis.Redis, 
                 trader_analyzer: TraderAnalyzer, config):
        self.db_pool = db_pool
        self.redis = redis_client
        self.analyzer = trader_analyzer
        self.config = config
        
        # Cache settings
        self.cache_ttl = 300  # 5 minutes
        
    async def get_top_traders(self, limit: int = 50, window: str = '30d') -> List[Dict]:
        """Get ranked list of top traders with AI scoring"""
        try:
            # Check cache first
            cache_key = f"leaderboard:{window}:{limit}"
            cached = await self.redis.get(cache_key)
            
            if cached:
                data = json.loads(cached)
                # Tolerate either a single object or list being cached
                if isinstance(data, dict):
                    return [data]
                return data
            
            # Fetch from database with filters
            traders = await self._fetch_filtered_traders(window)
            
            # Apply ranking algorithm
            ranked_traders = await self._rank_traders(traders)
            
            # Add AI analysis
            enriched_traders = await self._enrich_with_ai_analysis(ranked_traders)
            
            # Take top N
            top_traders = enriched_traders[:limit]
            
            # Cache for 5 minutes
            await self.redis.setex(cache_key, self.cache_ttl, json.dumps(top_traders, default=str))
            
            logger.info(f"Generated leaderboard with {len(top_traders)} traders")
            return top_traders
            
        except Exception as e:
            logger.error(f"Error getting top traders: {e}")
            return []
    
    async def _fetch_filtered_traders(self, window: str) -> List[Dict]:
        """Fetch traders that meet quality criteria"""
        try:
            query = """
                SELECT ts.*, ta.archetype, ta.risk_level, ta.sharpe_like, ta.consistency
                FROM trader_stats ts
                LEFT JOIN trader_analytics ta ON ts.address = ta.address AND ts.window = ta.window
                WHERE ts.window = $1
                  AND ts.last_trade_at > NOW() - INTERVAL '%s hours'
                  AND ts.trade_count_30d >= $3
                  AND ts.last_30d_volume_usd >= $4
                  AND (ts.maker_ratio IS NULL OR ts.maker_ratio <= 0.95)
                  AND ts.unique_symbols >= 3
                ORDER BY ts.last_30d_volume_usd DESC
            """ % self.config.LEADER_ACTIVE_HOURS
            
            acq = await self.db_pool.acquire()
            async with acq as conn:
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
            if not traders:
                return []
            
            for trader in traders:
                # Calculate individual scores
                volume_score = self._calculate_volume_score(trader['last_30d_volume_usd'])
                pnl_score = self._calculate_pnl_score(trader['realized_pnl_clean_usd'], trader['last_30d_volume_usd'])
                consistency_score = self._calculate_consistency_score(trader)
                recency_score = self._calculate_recency_score(trader['last_trade_at'])
                
                # Composite ranking score
                trader['ranking_score'] = (
                    volume_score * 0.4 +
                    pnl_score * 0.3 +
                    consistency_score * 0.2 +
                    recency_score * 0.1
                )
                
                # Store individual scores for analysis
                trader['volume_score'] = volume_score
                trader['pnl_score'] = pnl_score
                trader['consistency_score'] = consistency_score
                trader['recency_score'] = recency_score
            
            # Sort by composite score
            ranked_traders = sorted(traders, key=lambda x: x['ranking_score'], reverse=True)
            
            return ranked_traders
            
        except Exception as e:
            logger.error(f"Error ranking traders: {e}")
            return traders
    
    def _calculate_volume_score(self, volume: float) -> float:
        """Calculate volume-based score (0-1)"""
        if volume <= 0:
            return 0.0
        
        # Log-normalized volume score
        log_volume = np.log1p(volume)
        max_log_volume = 20  # Approximate max for normalization
        
        return min(1.0, log_volume / max_log_volume)
    
    def _calculate_pnl_score(self, pnl: float, volume: float) -> float:
        """Calculate PnL-based score (0-1)"""
        if volume <= 0:
            return 0.5  # Neutral score for no volume
        
        # ROI-based scoring
        roi = pnl / volume
        
        # Normalize to 0-1 range
        # Positive ROI gets higher scores, negative ROI gets lower scores
        if roi >= 0:
            # Positive ROI: 0.5 to 1.0
            return 0.5 + min(0.5, roi * 10)  # Cap at 5% ROI for max score
        else:
            # Negative ROI: 0.0 to 0.5
            return max(0.0, 0.5 + roi * 10)  # Cap at -5% ROI for min score
    
    def _calculate_consistency_score(self, trader: Dict) -> float:
        """Calculate consistency-based score (0-1)"""
        try:
            # Use AI consistency if available
            if trader.get('consistency') is not None:
                return float(trader['consistency'])
            
            # Fallback: use trade count and unique symbols as proxy
            trade_count = trader.get('trade_count_30d', 0)
            unique_symbols = trader.get('unique_symbols', 0)
            
            if trade_count == 0:
                return 0.0
            
            # Consistency based on diversification and activity
            diversification_score = min(1.0, unique_symbols / 10)  # Up to 10 symbols
            activity_score = min(1.0, trade_count / 1000)  # Up to 1000 trades
            
            return (diversification_score + activity_score) / 2
            
        except Exception as e:
            logger.error(f"Error calculating consistency score: {e}")
            return 0.5
    
    def _calculate_recency_score(self, last_trade_at: Optional[datetime]) -> float:
        """Calculate recency-based score (0-1)"""
        if not last_trade_at:
            return 0.0
        
        delta = datetime.utcnow() - last_trade_at
        hours_ago = delta.total_seconds() / 3600
        # Be lenient for boundary conditions to account for computation drift
        if delta <= timedelta(hours=1, seconds=5):
            return 1.0
        if delta <= timedelta(hours=24, seconds=5):
            return 0.8
        if delta <= timedelta(days=7, seconds=5):  # up to 1 week
            return 0.2
        return 0.0
    
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
            acq = await self.db_pool.acquire()
            async with acq as conn:
                row = await conn.fetchrow("""
                    SELECT archetype, risk_level, sharpe_like, max_drawdown, 
                           consistency, win_prob_7d, expected_dd_7d, optimal_copy_ratio
                    FROM trader_analytics
                    WHERE address = $1 AND window = '30d'
                """, address)
                
                if row:
                    analysis = dict(row)
                    
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
            consistency_factor = trader.get('consistency_score', 0.5) * 15
            
            # Risk factor (medium risk preferred for copying)
            risk_level = trader.get('risk_level', 'MED')
            risk_factor = {'LOW': 5, 'MED': 15, 'HIGH': -10}.get(risk_level, 0)
            
            # PnL factor (positive PnL preferred)
            pnl_factor = trader.get('pnl_score', 0.5) * 10
            
            # Archetype factor (some archetypes copy better)
            archetype = trader.get('archetype', 'Unknown')
            archetype_factor = {
                'Conservative Scalper': 10,
                'Risk Manager': 15,
                'Precision Trader': 12,
                'Volume Hunter': 5,
                'Aggressive Swinger': -5
            }.get(archetype, 0)
            
            # Recency factor (more recent activity preferred)
            recency_factor = trader.get('recency_score', 0.5) * 10
            
            total_score = (base_score + volume_factor + consistency_factor + 
                          risk_factor + pnl_factor + archetype_factor + recency_factor)
            
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
                **(ai_analysis or {}),
                'recent_trades': recent_trades,
                'copyability_score': self._calculate_copyability_score({**stats, **(ai_analysis or {})}),
                'strengths': self._identify_strengths(stats, ai_analysis),
                'warnings': self._identify_warnings(stats, ai_analysis),
                'optimal_copy_size': self._suggest_copy_size(stats, ai_analysis)
            }
            
            return card_data
            
        except Exception as e:
            logger.error(f"Error getting trader card for {address}: {e}")
            return None
    
    async def _get_trader_stats(self, address: str) -> Optional[Dict]:
        """Get trader statistics"""
        try:
            acq = await self.db_pool.acquire()
            async with acq as conn:
                row = await conn.fetchrow("""
                    SELECT * FROM trader_stats
                    WHERE address = $1 AND window = '30d'
                """, address)
                
                return dict(row) if row else None
                
        except Exception as e:
            logger.error(f"Error getting trader stats for {address}: {e}")
            return None
    
    async def _get_recent_trades(self, address: str, limit: int = 10) -> List[Dict]:
        """Get recent trades for a trader"""
        try:
            acq = await self.db_pool.acquire()
            async with acq as conn:
                rows = await conn.fetch("""
                    SELECT pair, is_long, size, price, leverage, timestamp, event_type
                    FROM trade_events
                    WHERE address = $1
                    ORDER BY timestamp DESC
                    LIMIT $2
                """, address, limit)
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting recent trades for {address}: {e}")
            return []
    
    def _identify_strengths(self, stats: Dict, ai_analysis: Optional[Dict]) -> List[str]:
        """Identify trader strengths"""
        strengths = []
        
        try:
            # Volume strength
            if stats.get('last_30d_volume_usd', 0) > 1000000:  # $1M+
                strengths.append("High trading volume")
            
            # PnL strength
            if stats.get('realized_pnl_clean_usd', 0) > 0:
                strengths.append("Positive PnL track record")
            
            # Activity strength
            if stats.get('trade_count_30d', 0) > 500:
                strengths.append("High trading activity")
            
            # Diversification strength
            if stats.get('unique_symbols', 0) > 5:
                strengths.append("Well-diversified portfolio")
            
            # AI-based strengths
            if ai_analysis:
                archetype = ai_analysis.get('archetype', '')
                if archetype == 'Conservative Scalper':
                    strengths.append("Conservative risk management")
                elif archetype == 'Risk Manager':
                    strengths.append("Excellent risk control")
                elif archetype == 'Precision Trader':
                    strengths.append("Precise entry/exit timing")
                
                # Consistency strength
                if ai_analysis.get('consistency', 0) > 0.7:
                    strengths.append("Consistent performance")
            
            return strengths[:3]  # Return top 3
            
        except Exception as e:
            logger.error(f"Error identifying strengths: {e}")
            return ["Analysis pending"]
    
    def _identify_warnings(self, stats: Dict, ai_analysis: Optional[Dict]) -> List[str]:
        """Identify potential warnings"""
        warnings = []
        
        try:
            # PnL warnings
            if stats.get('realized_pnl_clean_usd', 0) < -10000:  # -$10k
                warnings.append("Significant losses")
            
            # Volume warnings
            if stats.get('last_30d_volume_usd', 0) < 100000:  # <$100k
                warnings.append("Low trading volume")
            
            # Activity warnings
            if stats.get('trade_count_30d', 0) < 50:
                warnings.append("Limited trading activity")
            
            # AI-based warnings
            if ai_analysis:
                risk_level = ai_analysis.get('risk_level', '')
                if risk_level == 'HIGH':
                    warnings.append("High risk profile")
                
                max_drawdown = ai_analysis.get('max_drawdown', 0)
                if max_drawdown > 0.2:  # 20%
                    warnings.append("High historical drawdown")
            
            return warnings[:2]  # Return top 2
            
        except Exception as e:
            logger.error(f"Error identifying warnings: {e}")
            return []
    
    def _suggest_copy_size(self, stats: Dict, ai_analysis: Optional[Dict]) -> float:
        """Suggest optimal copy size for this trader"""
        try:
            # Base suggestion
            base_size = 100.0  # $100
            
            # Adjust based on volume
            volume = stats.get('last_30d_volume_usd', 0)
            if volume > 10000000:  # $10M+
                base_size *= 2
            elif volume > 1000000:  # $1M+
                base_size *= 1.5
            elif volume < 100000:  # <$100k
                base_size *= 0.5
            
            # Adjust based on AI analysis
            if ai_analysis:
                risk_level = ai_analysis.get('risk_level', '')
                if risk_level == 'LOW':
                    base_size *= 1.2
                elif risk_level == 'HIGH':
                    base_size *= 0.8
                
                optimal_ratio = ai_analysis.get('optimal_copy_ratio', 0.1)
                if optimal_ratio > 0:
                    base_size *= optimal_ratio * 10  # Scale up the ratio
            
            # Cap at reasonable limits
            return max(10.0, min(1000.0, base_size))
            
        except Exception as e:
            logger.error(f"Error suggesting copy size: {e}")
            return 100.0
    
    async def get_leaderboard_by_category(self, category: str, limit: int = 20) -> List[Dict]:
        """Get leaderboard filtered by category"""
        try:
            all_traders = await self.get_top_traders(limit=100)
            
            if category == 'volume':
                # Sort by volume
                return sorted(all_traders, key=lambda x: x.get('last_30d_volume_usd', 0), reverse=True)[:limit]
            
            elif category == 'pnl':
                # Sort by PnL
                return sorted(all_traders, key=lambda x: x.get('realized_pnl_clean_usd', 0), reverse=True)[:limit]
            
            elif category == 'consistency':
                # Sort by consistency score
                return sorted(all_traders, key=lambda x: x.get('consistency_score', 0), reverse=True)[:limit]
            
            elif category == 'copyability':
                # Sort by copyability score
                return sorted(all_traders, key=lambda x: x.get('copyability_score', 50), reverse=True)[:limit]
            
            else:
                # Default: overall ranking
                return all_traders[:limit]
                
        except Exception as e:
            logger.error(f"Error getting leaderboard by category {category}: {e}")
            return []
    
    async def search_traders(self, query: str, limit: int = 10) -> List[Dict]:
        """Search traders by address or other criteria"""
        try:
            # For now, simple address matching
            # In production, this could be more sophisticated
            
            if not query.startswith('0x') or len(query) < 6:
                return []
            
            # Get trader stats for addresses that match
            acq = await self.db_pool.acquire()
            async with acq as conn:
                rows = await conn.fetch("""
                    SELECT * FROM trader_stats
                    WHERE address ILIKE $1 AND window = '30d'
                    ORDER BY last_30d_volume_usd DESC
                    LIMIT $2
                """, f'%{query}%', limit)
            
            traders = []
            for row in rows:
                trader_data = dict(row)
                
                # Add AI analysis
                ai_analysis = await self._get_ai_analysis(row['address'])
                if ai_analysis:
                    trader_data.update(ai_analysis)
                
                # Calculate copyability score
                trader_data['copyability_score'] = self._calculate_copyability_score(trader_data)
                
                traders.append(trader_data)
            
            return traders
            
        except Exception as e:
            logger.error(f"Error searching traders: {e}")
            return []
    
    async def get_trader_analytics_summary(self) -> Dict[str, Any]:
        """Get summary analytics for all traders"""
        try:
            # Get basic counts
            acq = await self.db_pool.acquire()
            async with acq as conn:
                total_traders = await conn.fetchval("SELECT COUNT(*) FROM trader_stats WHERE window = '30d'")
                active_traders = await conn.fetchval("""
                    SELECT COUNT(*) FROM trader_stats 
                    WHERE window = '30d' AND last_trade_at > NOW() - INTERVAL '24 hours'
                """)
                
                # Get volume stats
                volume_stats = await conn.fetchrow("""
                    SELECT 
                        AVG(last_30d_volume_usd) as avg_volume,
                        MAX(last_30d_volume_usd) as max_volume,
                        MIN(last_30d_volume_usd) as min_volume
                    FROM trader_stats WHERE window = '30d'
                """)
                
                # Get archetype distribution
                archetype_dist = await conn.fetch("""
                    SELECT archetype, COUNT(*) as count
                    FROM trader_analytics
                    WHERE window = '30d'
                    GROUP BY archetype
                    ORDER BY count DESC
                """)
            
            return {
                'total_traders': total_traders,
                'active_traders': active_traders,
                'volume_stats': dict(volume_stats) if volume_stats else {},
                'archetype_distribution': [dict(row) for row in archetype_dist],
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting trader analytics summary: {e}")
            return {
                'total_traders': 0,
                'active_traders': 0,
                'volume_stats': {},
                'archetype_distribution': [],
                'last_updated': datetime.utcnow().isoformat()
            }
