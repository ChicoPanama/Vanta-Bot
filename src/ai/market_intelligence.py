"""
Market Intelligence System for Vanta Bot
Monitors market conditions and provides copy trading timing signals
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import numpy as np
import pandas as pd
import asyncpg
import redis.asyncio as redis
import aiohttp

logger = logging.getLogger(__name__)

@dataclass
class MarketRegime:
    """Market regime data structure"""
    symbol: str
    volatility: float
    trend: str
    regime_color: str
    confidence: float
    price_data: Dict[str, Any]
    updated_at: datetime

@dataclass
class CopyTimingSignal:
    """Copy timing signal data structure"""
    signal: str  # 'green', 'yellow', 'red'
    confidence: float
    volatility: float
    trend: str
    reason: str
    recommendation: str

class MarketIntelligence:
    """Market intelligence and regime detection system"""
    
    def __init__(self, config, db_pool: asyncpg.Pool, redis_client: redis.Redis):
        self.config = config
        self.db_pool = db_pool
        self.redis = redis_client
        self.price_feeds = {}
        self.regime_data = {}
        self.session = None
        
        # Load Pyth price feed IDs
        self.pyth_ids = json.loads(config.PYTH_PRICE_FEED_IDS_JSON)
        
    async def start_monitoring(self):
        """Start market intelligence monitoring"""
        logger.info("Starting market intelligence monitoring...")
        
        # Initialize HTTP session
        self.session = aiohttp.ClientSession()
        
        # Start price monitoring for all symbols
        tasks = []
        for symbol, pyth_id in self.pyth_ids.items():
            task = asyncio.create_task(self._monitor_price_feed(symbol, pyth_id))
            tasks.append(task)
        
        # Start regime analysis task
        regime_task = asyncio.create_task(self._periodic_regime_analysis())
        tasks.append(regime_task)
        
        # Start signal generation task
        signal_task = asyncio.create_task(self._generate_timing_signals())
        tasks.append(signal_task)
        
        # Wait for all tasks
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _monitor_price_feed(self, symbol: str, pyth_id: str):
        """Monitor individual price feed for regime changes"""
        logger.info(f"Starting price monitoring for {symbol}")
        
        while True:
            try:
                # Fetch price data from Pyth
                price_data = await self._fetch_pyth_price(pyth_id)
                
                if price_data:
                    await self._update_price_data(symbol, price_data)
                    await self._update_regime_analysis(symbol, price_data)
                
                # Update every 5 seconds
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error monitoring {symbol}: {e}")
                await asyncio.sleep(30)
    
    async def _fetch_pyth_price(self, pyth_id: str) -> Optional[Dict]:
        """Fetch price data from Pyth price feed"""
        try:
            # This is a simplified implementation
            # In practice, you'd connect to Pyth's WebSocket API or use their HTTP API
            
            # For now, we'll simulate price data
            # Replace this with actual Pyth integration
            current_time = datetime.utcnow()
            
            # Simulate price data (replace with real Pyth API call)
            base_price = 50000 if "BTC" in pyth_id else 3000 if "ETH" in pyth_id else 100
            
            # Add some realistic price movement
            import random
            price_change = random.uniform(-0.02, 0.02)  # ±2% change
            current_price = base_price * (1 + price_change)
            
            return {
                'price': current_price,
                'timestamp': current_time,
                'confidence': 0.95,
                'exponent': -8,
                'publish_time': int(current_time.timestamp())
            }
            
        except Exception as e:
            logger.error(f"Error fetching Pyth price for {pyth_id}: {e}")
            return None
    
    async def _update_price_data(self, symbol: str, price_data: Dict):
        """Update price data in memory and cache"""
        try:
            if symbol not in self.price_feeds:
                self.price_feeds[symbol] = {
                    'prices': [],
                    'last_updated': None
                }
            
            # Add new price point
            self.price_feeds[symbol]['prices'].append({
                'price': price_data['price'],
                'timestamp': price_data['timestamp'],
                'confidence': price_data.get('confidence', 1.0)
            })
            
            # Keep only last 24 hours of data (5-second intervals = 17,280 points)
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            self.price_feeds[symbol]['prices'] = [
                p for p in self.price_feeds[symbol]['prices'] 
                if p['timestamp'] > cutoff_time
            ]
            
            self.price_feeds[symbol]['last_updated'] = datetime.utcnow()
            
            # Cache in Redis
            cache_key = f"price_data:{symbol}"
            await self.redis.setex(
                cache_key,
                300,  # 5 minutes
                json.dumps({
                    'price': price_data['price'],
                    'timestamp': price_data['timestamp'].isoformat(),
                    'confidence': price_data.get('confidence', 1.0)
                })
            )
            
        except Exception as e:
            logger.error(f"Error updating price data for {symbol}: {e}")
    
    async def _update_regime_analysis(self, symbol: str, price_data: Dict):
        """Update regime analysis for a symbol"""
        try:
            if symbol not in self.regime_data:
                self.regime_data[symbol] = {
                    'volatility': 0.0,
                    'trend': 'neutral',
                    'regime_color': 'yellow',
                    'confidence': 0.5,
                    'last_updated': datetime.utcnow()
                }
            
            # Calculate regime metrics
            regime_metrics = await self._calculate_regime_metrics(symbol)
            
            if regime_metrics:
                self.regime_data[symbol].update(regime_metrics)
                self.regime_data[symbol]['last_updated'] = datetime.utcnow()
                
                # Store in database
                await self._store_regime_data(symbol, regime_metrics)
            
        except Exception as e:
            logger.error(f"Error updating regime analysis for {symbol}: {e}")
    
    async def _calculate_regime_metrics(self, symbol: str) -> Optional[Dict]:
        """Calculate volatility and trend for regime classification"""
        try:
            if symbol not in self.price_feeds or len(self.price_feeds[symbol]['prices']) < 20:
                return None
            
            prices = [p['price'] for p in self.price_feeds[symbol]['prices']]
            timestamps = [p['timestamp'] for p in self.price_feeds[symbol]['prices']]
            
            # Calculate 1-hour volatility (last 12 data points at 5-second intervals)
            recent_prices = prices[-12:] if len(prices) >= 12 else prices
            if len(recent_prices) < 2:
                return None
            
            # Calculate returns
            returns = []
            for i in range(1, len(recent_prices)):
                if recent_prices[i-1] > 0:
                    ret = np.log(recent_prices[i] / recent_prices[i-1])
                    returns.append(ret)
            
            if len(returns) < 2:
                return None
            
            # Calculate volatility (annualized)
            volatility = np.std(returns) * np.sqrt(720)  # 720 = 5-second intervals per hour
            
            # Calculate trend (4-hour momentum)
            trend = 'neutral'
            if len(prices) >= 288:  # 4 hours of data (288 * 5 seconds)
                trend_return = (prices[-1] - prices[-288]) / prices[-288]
                if trend_return > 0.02:  # 2% threshold
                    trend = 'bullish'
                elif trend_return < -0.02:
                    trend = 'bearish'
            
            # Determine regime color
            regime_color = self._determine_regime_color(volatility, trend)
            
            # Calculate confidence based on data quality
            confidence = min(1.0, len(prices) / 1000)  # More data = higher confidence
            
            return {
                'volatility': volatility,
                'trend': trend,
                'regime_color': regime_color,
                'confidence': confidence
            }
            
        except Exception as e:
            logger.error(f"Error calculating regime metrics for {symbol}: {e}")
            return None
    
    def _determine_regime_color(self, volatility: float, trend: str) -> str:
        """Determine if market conditions are favorable for copying"""
        # Green: Low volatility, any trend
        if volatility < 0.3:
            return 'green'
        
        # Yellow: Medium volatility
        elif volatility < 0.6:
            return 'yellow'
        
        # Red: High volatility (risky for copying)
        else:
            return 'red'
    
    async def _store_regime_data(self, symbol: str, regime_metrics: Dict):
        """Store regime data in database"""
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    INSERT INTO market_regime_data (
                        symbol, volatility, trend, regime_color, confidence, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (symbol) DO UPDATE SET
                        volatility = EXCLUDED.volatility,
                        trend = EXCLUDED.trend,
                        regime_color = EXCLUDED.regime_color,
                        confidence = EXCLUDED.confidence,
                        updated_at = EXCLUDED.updated_at
                """
                
                await conn.execute(
                    query,
                    symbol,
                    regime_metrics['volatility'],
                    regime_metrics['trend'],
                    regime_metrics['regime_color'],
                    regime_metrics['confidence'],
                    datetime.utcnow()
                )
                
        except Exception as e:
            logger.error(f"Error storing regime data for {symbol}: {e}")
    
    async def _periodic_regime_analysis(self):
        """Periodic regime analysis for all symbols"""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                
                # Update regime analysis for all symbols
                for symbol in self.pyth_ids.keys():
                    if symbol in self.price_feeds and self.price_feeds[symbol]['prices']:
                        regime_metrics = await self._calculate_regime_metrics(symbol)
                        if regime_metrics:
                            await self._store_regime_data(symbol, regime_metrics)
                
            except Exception as e:
                logger.error(f"Error in periodic regime analysis: {e}")
                await asyncio.sleep(60)
    
    async def _generate_timing_signals(self):
        """Generate copy timing signals"""
        while True:
            try:
                await asyncio.sleep(30)  # Generate signals every 30 seconds
                
                # Generate signals for all symbols
                for symbol in self.pyth_ids.keys():
                    signal = await self.get_copy_timing_signal(symbol)
                    
                    # Cache signal
                    cache_key = f"copy_signal:{symbol}"
                    await self.redis.setex(
                        cache_key,
                        60,  # 1 minute
                        json.dumps({
                            'signal': signal.signal,
                            'confidence': signal.confidence,
                            'volatility': signal.volatility,
                            'trend': signal.trend,
                            'reason': signal.reason,
                            'recommendation': signal.recommendation,
                            'timestamp': datetime.utcnow().isoformat()
                        })
                    )
                
            except Exception as e:
                logger.error(f"Error generating timing signals: {e}")
                await asyncio.sleep(30)
    
    async def get_copy_timing_signal(self, symbol: str) -> CopyTimingSignal:
        """Get current timing recommendation for copying trades"""
        try:
            # Check cache first
            cache_key = f"copy_signal:{symbol}"
            cached_signal = await self.redis.get(cache_key)
            
            if cached_signal:
                data = json.loads(cached_signal)
                return CopyTimingSignal(
                    signal=data['signal'],
                    confidence=data['confidence'],
                    volatility=data['volatility'],
                    trend=data['trend'],
                    reason=data['reason'],
                    recommendation=data['recommendation']
                )
            
            # Get regime data
            if symbol not in self.regime_data:
                return CopyTimingSignal(
                    signal='yellow',
                    confidence=0.3,
                    volatility=0.0,
                    trend='neutral',
                    reason='Insufficient data',
                    recommendation='Wait for more data before copying'
                )
            
            regime_info = self.regime_data[symbol]
            
            # Generate signal based on regime
            signal = regime_info['regime_color']
            confidence = regime_info['confidence']
            volatility = regime_info['volatility']
            trend = regime_info['trend']
            
            # Generate reason and recommendation
            reason = self._generate_signal_reason(regime_info)
            recommendation = self._generate_recommendation(signal, volatility, trend)
            
            return CopyTimingSignal(
                signal=signal,
                confidence=confidence,
                volatility=volatility,
                trend=trend,
                reason=reason,
                recommendation=recommendation
            )
            
        except Exception as e:
            logger.error(f"Error getting copy timing signal for {symbol}: {e}")
            return CopyTimingSignal(
                signal='yellow',
                confidence=0.3,
                volatility=0.0,
                trend='neutral',
                reason='Error in analysis',
                recommendation='Proceed with caution'
            )
    
    def _generate_signal_reason(self, regime_info: Dict) -> str:
        """Generate human-readable reason for signal"""
        vol = regime_info['volatility']
        trend = regime_info['trend']
        signal = regime_info['regime_color']
        
        if signal == 'green':
            return f"Low volatility ({vol:.1%}), {trend} trend - Good for copying"
        elif signal == 'yellow':
            return f"Moderate volatility ({vol:.1%}), {trend} trend - Copy with caution"
        else:
            return f"High volatility ({vol:.1%}), {trend} trend - Risky for copying"
    
    def _generate_recommendation(self, signal: str, volatility: float, trend: str) -> str:
        """Generate copy trading recommendation"""
        if signal == 'green':
            if trend == 'bullish':
                return "Favorable conditions - Consider following bullish traders"
            elif trend == 'bearish':
                return "Favorable conditions - Consider following bearish traders"
            else:
                return "Stable conditions - Good for all types of copy trading"
        
        elif signal == 'yellow':
            return "Moderate risk - Copy with smaller position sizes"
        
        else:  # red
            return "High risk - Avoid new copy trades or use very small sizes"
    
    async def get_all_signals(self) -> Dict[str, CopyTimingSignal]:
        """Get copy timing signals for all symbols"""
        signals = {}
        
        for symbol in self.pyth_ids.keys():
            signals[symbol] = await self.get_copy_timing_signal(symbol)
        
        return signals
    
    async def get_overall_regime(self) -> Dict[str, Any]:
        """Get overall market regime summary"""
        try:
            # Get all signals
            signals = await self.get_all_signals()
            
            # Count signals by color
            green_count = sum(1 for s in signals.values() if s.signal == 'green')
            yellow_count = sum(1 for s in signals.values() if s.signal == 'yellow')
            red_count = sum(1 for s in signals.values() if s.signal == 'red')
            
            total_signals = len(signals)
            
            # Determine overall regime
            if green_count >= total_signals * 0.6:
                regime_name = "Favorable"
                regime_color = "green"
            elif red_count >= total_signals * 0.4:
                regime_name = "High Risk"
                regime_color = "red"
            else:
                regime_name = "Mixed"
                regime_color = "yellow"
            
            # Calculate average volatility
            avg_volatility = np.mean([s.volatility for s in signals.values()])
            
            # Determine overall trend
            bullish_count = sum(1 for s in signals.values() if s.trend == 'bullish')
            bearish_count = sum(1 for s in signals.values() if s.trend == 'bearish')
            
            if bullish_count > bearish_count:
                overall_trend = 'bullish'
            elif bearish_count > bullish_count:
                overall_trend = 'bearish'
            else:
                overall_trend = 'neutral'
            
            return {
                'name': regime_name,
                'color': regime_color,
                'volatility': avg_volatility,
                'trend': overall_trend,
                'signal_counts': {
                    'green': green_count,
                    'yellow': yellow_count,
                    'red': red_count
                },
                'total_symbols': total_signals,
                'confidence': np.mean([s.confidence for s in signals.values()])
            }
            
        except Exception as e:
            logger.error(f"Error getting overall regime: {e}")
            return {
                'name': 'Unknown',
                'color': 'yellow',
                'volatility': 0.0,
                'trend': 'neutral',
                'signal_counts': {'green': 0, 'yellow': 0, 'red': 0},
                'total_symbols': 0,
                'confidence': 0.0
            }
    
    async def get_historical_regime_data(self, symbol: str, hours: int = 24) -> List[Dict]:
        """Get historical regime data for a symbol"""
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT * FROM market_regime_data 
                    WHERE symbol = $1 AND updated_at >= $2
                    ORDER BY updated_at ASC
                """
                
                since = datetime.utcnow() - timedelta(hours=hours)
                rows = await conn.fetch(query, symbol, since)
                
                return [
                    {
                        'symbol': row['symbol'],
                        'volatility': float(row['volatility']),
                        'trend': row['trend'],
                        'regime_color': row['regime_color'],
                        'confidence': float(row['confidence']),
                        'updated_at': row['updated_at']
                    }
                    for row in rows
                ]
                
        except Exception as e:
            logger.error(f"Error getting historical regime data for {symbol}: {e}")
            return []
    
    async def get_volatility_forecast(self, symbol: str, hours_ahead: int = 24) -> Dict[str, float]:
        """Generate volatility forecast for a symbol"""
        try:
            # Get historical volatility data
            historical_data = await self.get_historical_regime_data(symbol, hours=48)
            
            if len(historical_data) < 10:
                return {
                    'forecast_volatility': 0.3,
                    'confidence': 0.3,
                    'trend': 'stable'
                }
            
            # Extract volatility values
            volatilities = [d['volatility'] for d in historical_data]
            
            # Simple moving average forecast
            recent_vol = np.mean(volatilities[-6:])  # Last 6 data points
            older_vol = np.mean(volatilities[-12:-6])  # Previous 6 data points
            
            # Calculate trend
            if recent_vol > older_vol * 1.1:
                trend = 'increasing'
            elif recent_vol < older_vol * 0.9:
                trend = 'decreasing'
            else:
                trend = 'stable'
            
            # Forecast (simple linear extrapolation)
            forecast_vol = recent_vol * (1 + (recent_vol - older_vol) / max(older_vol, 0.001))
            forecast_vol = max(0.01, min(2.0, forecast_vol))  # Clamp to reasonable range
            
            # Confidence based on data consistency
            vol_std = np.std(volatilities[-12:])
            confidence = max(0.1, min(1.0, 1.0 - vol_std / max(np.mean(volatilities[-12:]), 0.001)))
            
            return {
                'forecast_volatility': forecast_vol,
                'confidence': confidence,
                'trend': trend,
                'current_volatility': recent_vol
            }
            
        except Exception as e:
            logger.error(f"Error generating volatility forecast for {symbol}: {e}")
            return {
                'forecast_volatility': 0.3,
                'confidence': 0.3,
                'trend': 'stable'
            }
    
    async def get_copy_opportunities(self) -> List[Dict[str, Any]]:
        """Identify current copy trading opportunities"""
        try:
            opportunities = []
            
            # Get all signals
            signals = await self.get_all_signals()
            
            # Get overall regime
            overall_regime = await self.get_overall_regime()
            
            # Identify opportunities based on signals and regime
            for symbol, signal in signals.items():
                if signal.signal == 'green' and signal.confidence > 0.6:
                    # High-quality opportunity
                    opportunity = {
                        'symbol': symbol,
                        'type': 'high_quality',
                        'signal': signal.signal,
                        'confidence': signal.confidence,
                        'volatility': signal.volatility,
                        'trend': signal.trend,
                        'reason': signal.reason,
                        'recommendation': signal.recommendation,
                        'priority': 'high'
                    }
                    opportunities.append(opportunity)
                
                elif signal.signal == 'yellow' and signal.confidence > 0.7:
                    # Moderate opportunity
                    opportunity = {
                        'symbol': symbol,
                        'type': 'moderate',
                        'signal': signal.signal,
                        'confidence': signal.confidence,
                        'volatility': signal.volatility,
                        'trend': signal.trend,
                        'reason': signal.reason,
                        'recommendation': signal.recommendation,
                        'priority': 'medium'
                    }
                    opportunities.append(opportunity)
            
            # Sort by confidence and priority
            opportunities.sort(key=lambda x: (x['priority'] == 'high', x['confidence']), reverse=True)
            
            return opportunities[:5]  # Return top 5 opportunities
            
        except Exception as e:
            logger.error(f"Error identifying copy opportunities: {e}")
            return []
    
    async def stop(self):
        """Stop the market intelligence service"""
        logger.info("Stopping market intelligence service...")
        
        if self.session:
            await self.session.close()
        
        # Cleanup resources if needed
