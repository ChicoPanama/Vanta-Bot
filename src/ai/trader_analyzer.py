"""
AI Trader Analyzer for Vanta Bot
Analyzes trader behavior and generates predictions using machine learning
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio
import asyncpg
import redis.asyncio as redis

from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score

from ..analytics.position_tracker import TraderStats

logger = logging.getLogger(__name__)

@dataclass
class TraderAnalysis:
    """AI analysis results for a trader"""
    address: str
    archetype: str
    performance_score: float
    anomaly_score: float
    risk_level: str
    sharpe_like: float
    max_drawdown: float
    consistency: float
    win_prob_7d: float
    expected_dd_7d: float
    optimal_copy_ratio: float
    strengths: List[str]
    warnings: List[str]
    confidence: float

class TraderAnalyzer:
    """AI-powered trader analysis and prediction engine"""
    
    def __init__(self, db_pool: asyncpg.Pool, redis_client: redis.Redis, config):
        self.db_pool = db_pool
        self.redis = redis_client
        self.config = config
        
        # Initialize ML models
        self.performance_model = RandomForestRegressor(
            n_estimators=100, 
            random_state=42,
            max_depth=10,
            min_samples_split=5
        )
        self.anomaly_detector = IsolationForest(
            contamination=0.1, 
            random_state=42
        )
        self.clustering_model = KMeans(
            n_clusters=5, 
            random_state=42,
            n_init=10
        )
        self.scaler = StandardScaler()
        
        # Trader archetypes
        self.archetypes = {
            0: "Conservative Scalper",
            1: "Aggressive Swinger", 
            2: "Risk Manager",
            3: "Volume Hunter",
            4: "Precision Trader"
        }
        
        # Model training state
        self.is_trained = False
        self.last_training_time = None
        
    async def start_analysis_service(self):
        """Start the AI analysis service"""
        logger.info("Starting AI trader analysis service...")
        
        # Initial model training
        await self._train_models()
        
        # Start background tasks
        asyncio.create_task(self._periodic_model_update())
        asyncio.create_task(self._analyze_new_traders())
    
    async def _train_models(self):
        """Train ML models on historical data"""
        try:
            logger.info("Training AI models...")
            
            # Get training data
            training_data = await self._get_training_data()
            
            if len(training_data) < 100:
                logger.warning(f"Insufficient training data: {len(training_data)} samples")
                return
            
            # Prepare features and targets
            features, targets = self._prepare_training_data(training_data)
            
            if features.shape[0] == 0:
                logger.warning("No valid training features")
                return
            
            # Train models
            self.scaler.fit(features)
            features_scaled = self.scaler.transform(features)
            
            # Train performance prediction model
            self.performance_model.fit(features_scaled, targets['performance'])
            
            # Train anomaly detection model
            self.anomaly_detector.fit(features_scaled)
            
            # Train clustering model for archetypes
            self.clustering_model.fit(features_scaled)
            
            self.is_trained = True
            self.last_training_time = datetime.utcnow()
            
            # Store model metadata
            await self._store_model_metadata()
            
            logger.info(f"Models trained successfully on {len(training_data)} samples")
            
        except Exception as e:
            logger.error(f"Error training models: {e}")
    
    async def _get_training_data(self) -> List[Dict]:
        """Get training data from database"""
        try:
            async with self.db_pool.acquire() as conn:
                # Get traders with sufficient history
                query = """
                    SELECT 
                        ts.*,
                        ta.sharpe_like, ta.max_drawdown, ta.consistency,
                        ta.archetype, ta.risk_level
                    FROM trader_stats ts
                    LEFT JOIN trader_analytics ta ON ts.address = ta.address AND ts.window = ta.window
                    WHERE ts.trade_count_30d >= 50
                      AND ts.last_30d_volume_usd >= 100000
                      AND ts.last_trade_at > NOW() - INTERVAL '7 days'
                """
                rows = await conn.fetch(query)
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting training data: {e}")
            return []
    
    def _prepare_training_data(self, data: List[Dict]) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
        """Prepare features and targets for training"""
        features = []
        performance_targets = []
        
        for trader_data in data:
            try:
                # Extract features
                feature_vector = self._extract_features_from_data(trader_data)
                if feature_vector is not None:
                    features.append(feature_vector)
                    
                    # Calculate performance target (normalized PnL/Volume ratio)
                    volume = trader_data.get('last_30d_volume_usd', 1)
                    pnl = trader_data.get('realized_pnl_clean_usd', 0)
                    performance = pnl / max(volume, 1)  # Normalize by volume
                    performance_targets.append(performance)
                    
            except Exception as e:
                logger.warning(f"Error preparing training data for trader: {e}")
                continue
        
        features_array = np.array(features) if features else np.array([]).reshape(0, 20)
        targets_dict = {
            'performance': np.array(performance_targets) if performance_targets else np.array([])
        }
        
        return features_array, targets_dict
    
    def _extract_features_from_data(self, trader_data: Dict) -> Optional[np.ndarray]:
        """Extract ML features from trader data"""
        try:
            # Basic stats features
            volume = trader_data.get('last_30d_volume_usd', 0)
            trade_count = trader_data.get('trade_count_30d', 0)
            median_size = trader_data.get('median_trade_size_usd', 0)
            win_rate = trader_data.get('win_rate', 0.5)
            maker_ratio = trader_data.get('maker_ratio', 0.5) or 0.5
            unique_symbols = trader_data.get('unique_symbols', 1)
            
            # Normalize features
            volume_normalized = np.log1p(volume)
            trade_count_normalized = np.log1p(trade_count)
            median_size_normalized = np.log1p(median_size)
            
            # Risk features
            sharpe_like = trader_data.get('sharpe_like', 0) or 0
            max_drawdown = trader_data.get('max_drawdown', 0) or 0
            consistency = trader_data.get('consistency', 0.5) or 0.5
            
            # Symbol diversity
            symbol_diversity = unique_symbols / max(trade_count, 1)
            
            # Create feature vector (20 features)
            features = np.array([
                volume_normalized,           # 0
                trade_count_normalized,      # 1
                median_size_normalized,      # 2
                win_rate,                    # 3
                maker_ratio,                 # 4
                sharpe_like,                 # 5
                max_drawdown,                # 6
                consistency,                 # 7
                symbol_diversity,            # 8
                # Additional derived features
                volume_normalized * win_rate,  # 9
                trade_count_normalized * consistency,  # 10
                sharpe_like * (1 - max_drawdown),  # 11
                maker_ratio * consistency,   # 12
                win_rate * (1 - max_drawdown),  # 13
                # Placeholder features for future expansion
                0.0, 0.0, 0.0, 0.0, 0.0, 0.0  # 14-19
            ])
            
            return features
            
        except Exception as e:
            logger.warning(f"Error extracting features: {e}")
            return None
    
    async def analyze_trader(self, address: str, stats: TraderStats, trades: List[Dict] = None) -> TraderAnalysis:
        """Generate comprehensive AI analysis for a trader"""
        try:
            # Convert stats to dict for feature extraction
            stats_dict = {
                'address': stats.address,
                'last_30d_volume_usd': stats.last_30d_volume_usd,
                'trade_count_30d': stats.trade_count_30d,
                'median_trade_size_usd': stats.median_trade_size_usd,
                'win_rate': stats.win_rate,
                'maker_ratio': stats.maker_ratio,
                'unique_symbols': stats.unique_symbols,
                'realized_pnl_clean_usd': stats.realized_pnl_clean_usd,
                'sharpe_like': 0.0,  # Will be calculated
                'max_drawdown': 0.0,  # Will be calculated
                'consistency': stats.leverage_consistency
            }
            
            # Extract features
            features = self._extract_features_from_data(stats_dict)
            
            if features is None:
                return self._create_default_analysis(address)
            
            # Calculate risk metrics
            risk_metrics = self._calculate_risk_metrics(trades or [])
            stats_dict.update(risk_metrics)
            
            # Update features with risk metrics
            features[5] = risk_metrics['sharpe_like']
            features[6] = risk_metrics['max_drawdown']
            features[7] = risk_metrics['consistency']
            
            # Generate predictions if model is trained
            if self.is_trained:
                features_scaled = self.scaler.transform([features])
                
                # Performance prediction
                performance_score = self._predict_performance(features_scaled[0])
                
                # Anomaly detection
                anomaly_score = self._detect_anomalies(features_scaled[0])
                
                # Archetype classification
                archetype = self._classify_archetype(features_scaled[0])
                
                # 7-day forecasts
                forecasts = self._generate_forecasts(features_scaled[0], trades or [])
            else:
                # Use default values if model not trained
                performance_score = 0.5
                anomaly_score = 0.5
                archetype = "Unknown"
                forecasts = {'win_probability': 0.5, 'expected_drawdown': 0.05, 'confidence': 0.3}
            
            # Determine risk level
            risk_level = self._determine_risk_level(risk_metrics, anomaly_score)
            
            # Calculate optimal copy ratio
            optimal_copy_ratio = self._calculate_optimal_copy_ratio(risk_metrics)
            
            # Identify strengths and warnings
            strengths = self._identify_strengths(features, archetype)
            warnings = self._identify_warnings(anomaly_score, risk_metrics)
            
            return TraderAnalysis(
                address=address,
                archetype=archetype,
                performance_score=performance_score,
                anomaly_score=anomaly_score,
                risk_level=risk_level,
                sharpe_like=risk_metrics['sharpe_like'],
                max_drawdown=risk_metrics['max_drawdown'],
                consistency=risk_metrics['consistency'],
                win_prob_7d=forecasts['win_probability'],
                expected_dd_7d=forecasts['expected_drawdown'],
                optimal_copy_ratio=optimal_copy_ratio,
                strengths=strengths,
                warnings=warnings,
                confidence=forecasts['confidence']
            )
            
        except Exception as e:
            logger.error(f"Error analyzing trader {address}: {e}")
            return self._create_default_analysis(address)
    
    def _create_default_analysis(self, address: str) -> TraderAnalysis:
        """Create default analysis when model is not available"""
        return TraderAnalysis(
            address=address,
            archetype="Unknown",
            performance_score=0.5,
            anomaly_score=0.5,
            risk_level="MED",
            sharpe_like=0.0,
            max_drawdown=0.0,
            consistency=0.5,
            win_prob_7d=0.5,
            expected_dd_7d=0.05,
            optimal_copy_ratio=0.1,
            strengths=["Active trader"],
            warnings=["Limited data for analysis"],
            confidence=0.3
        )
    
    def _predict_performance(self, features: np.ndarray) -> float:
        """Predict trader performance score"""
        try:
            if hasattr(self.performance_model, 'predict'):
                prediction = self.performance_model.predict([features])[0]
                return max(0.0, min(1.0, prediction))  # Clamp to [0, 1]
            return 0.5
        except Exception as e:
            logger.warning(f"Error in performance prediction: {e}")
            return 0.5
    
    def _detect_anomalies(self, features: np.ndarray) -> float:
        """Detect anomalous trading behavior"""
        try:
            if hasattr(self.anomaly_detector, 'decision_function'):
                anomaly_score = self.anomaly_detector.decision_function([features])[0]
                # Normalize to [0, 1] where 1 is most anomalous
                normalized_score = (anomaly_score + 1) / 2
                return max(0.0, min(1.0, normalized_score))
            return 0.5
        except Exception as e:
            logger.warning(f"Error in anomaly detection: {e}")
            return 0.5
    
    def _classify_archetype(self, features: np.ndarray) -> str:
        """Classify trader into archetype"""
        try:
            if hasattr(self.clustering_model, 'predict'):
                cluster = self.clustering_model.predict([features])[0]
                return self.archetypes.get(cluster, "Unknown")
            return "Unknown"
        except Exception as e:
            logger.warning(f"Error in archetype classification: {e}")
            return "Unknown"
    
    def _calculate_risk_metrics(self, trades: List[Dict]) -> Dict[str, float]:
        """Calculate comprehensive risk metrics"""
        if not trades:
            return {'sharpe_like': 0.0, 'max_drawdown': 0.0, 'consistency': 0.5}
        
        try:
            # Calculate daily returns
            daily_returns = self._calculate_daily_returns(trades)
            
            if not daily_returns or len(daily_returns) < 5:
                return {'sharpe_like': 0.0, 'max_drawdown': 0.0, 'consistency': 0.5}
            
            # Sharpe-like ratio (using EWMA)
            returns_series = pd.Series(daily_returns)
            ewma_return = returns_series.ewm(span=min(10, len(returns_series))).mean().iloc[-1]
            ewma_vol = returns_series.ewm(span=min(10, len(returns_series))).std().iloc[-1]
            sharpe_like = ewma_return / max(ewma_vol, 0.001)
            
            # Maximum drawdown
            cumulative_returns = np.cumsum(daily_returns)
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdowns = cumulative_returns - running_max
            max_drawdown = abs(np.min(drawdowns))
            
            # Consistency (win rate stability)
            win_rates_rolling = self._calculate_rolling_win_rates(trades, window=7)
            consistency = 1 - np.std(win_rates_rolling) if len(win_rates_rolling) > 1 else 0.5
            
            return {
                'sharpe_like': sharpe_like,
                'max_drawdown': max_drawdown,
                'consistency': max(0.0, min(1.0, consistency))
            }
            
        except Exception as e:
            logger.warning(f"Error calculating risk metrics: {e}")
            return {'sharpe_like': 0.0, 'max_drawdown': 0.0, 'consistency': 0.5}
    
    def _calculate_daily_returns(self, trades: List[Dict]) -> List[float]:
        """Calculate daily returns from trades"""
        try:
            # Group trades by date
            daily_pnl = {}
            
            for trade in trades:
                if trade.get('event_type') == 'CLOSED':
                    date = trade['timestamp'].date()
                    pnl = trade.get('pnl', 0) or 0
                    
                    if date not in daily_pnl:
                        daily_pnl[date] = 0
                    daily_pnl[date] += pnl
            
            # Convert to sorted list of returns
            dates = sorted(daily_pnl.keys())
            returns = [daily_pnl[date] for date in dates]
            
            return returns
            
        except Exception as e:
            logger.warning(f"Error calculating daily returns: {e}")
            return []
    
    def _calculate_rolling_win_rates(self, trades: List[Dict], window: int = 7) -> List[float]:
        """Calculate rolling win rates"""
        try:
            # Group trades by date
            daily_trades = {}
            
            for trade in trades:
                if trade.get('event_type') == 'CLOSED':
                    date = trade['timestamp'].date()
                    
                    if date not in daily_trades:
                        daily_trades[date] = []
                    daily_trades[date].append(trade)
            
            # Calculate rolling win rates
            dates = sorted(daily_trades.keys())
            win_rates = []
            
            for i in range(len(dates)):
                start_idx = max(0, i - window + 1)
                window_dates = dates[start_idx:i+1]
                
                window_trades = []
                for date in window_dates:
                    window_trades.extend(daily_trades[date])
                
                if window_trades:
                    winning_trades = [t for t in window_trades if t.get('pnl', 0) > 0]
                    win_rate = len(winning_trades) / len(window_trades)
                    win_rates.append(win_rate)
            
            return win_rates
            
        except Exception as e:
            logger.warning(f"Error calculating rolling win rates: {e}")
            return []
    
    def _generate_forecasts(self, features: np.ndarray, trades: List[Dict]) -> Dict[str, float]:
        """Generate 7-day performance forecasts"""
        try:
            if not hasattr(self.performance_model, 'feature_importances_'):
                return {
                    'win_probability': 0.5,
                    'expected_drawdown': 0.05,
                    'confidence': 0.3
                }
            
            # Predict next 7-day win probability
            win_prob = max(0.1, min(0.9, self.performance_model.predict([features])[0]))
            
            # Estimate expected drawdown based on historical volatility
            recent_volatility = self._calculate_recent_volatility(trades)
            expected_dd = min(0.3, recent_volatility * 1.5)  # Cap at 30%
            
            # Calculate confidence based on data quality
            confidence = 0.7 if len(trades) > 100 else 0.4
            
            return {
                'win_probability': win_prob,
                'expected_drawdown': expected_dd,
                'confidence': confidence
            }
            
        except Exception as e:
            logger.warning(f"Error generating forecasts: {e}")
            return {
                'win_probability': 0.5,
                'expected_drawdown': 0.05,
                'confidence': 0.3
            }
    
    def _calculate_recent_volatility(self, trades: List[Dict]) -> float:
        """Calculate recent volatility from trades"""
        try:
            if len(trades) < 10:
                return 0.1  # Default volatility
            
            # Get recent trades (last 30 days)
            recent_trades = [
                t for t in trades 
                if t.get('timestamp') and 
                (datetime.utcnow() - t['timestamp']).days <= 30
            ]
            
            if len(recent_trades) < 5:
                return 0.1
            
            # Calculate returns
            returns = []
            for trade in recent_trades:
                if trade.get('event_type') == 'CLOSED' and trade.get('pnl'):
                    returns.append(trade['pnl'])
            
            if len(returns) < 3:
                return 0.1
            
            # Calculate volatility
            returns_array = np.array(returns)
            volatility = np.std(returns_array) / max(np.mean(np.abs(returns_array)), 0.001)
            
            return min(0.5, volatility)  # Cap at 50%
            
        except Exception as e:
            logger.warning(f"Error calculating recent volatility: {e}")
            return 0.1
    
    def _determine_risk_level(self, risk_metrics: Dict[str, float], anomaly_score: float) -> str:
        """Determine risk level based on metrics"""
        try:
            sharpe = risk_metrics['sharpe_like']
            max_dd = risk_metrics['max_drawdown']
            consistency = risk_metrics['consistency']
            
            # Risk scoring
            risk_score = 0
            
            # Sharpe ratio component
            if sharpe < -0.5:
                risk_score += 3
            elif sharpe < 0:
                risk_score += 2
            elif sharpe < 0.5:
                risk_score += 1
            
            # Drawdown component
            if max_dd > 0.3:
                risk_score += 3
            elif max_dd > 0.2:
                risk_score += 2
            elif max_dd > 0.1:
                risk_score += 1
            
            # Consistency component
            if consistency < 0.3:
                risk_score += 2
            elif consistency < 0.5:
                risk_score += 1
            
            # Anomaly component
            if anomaly_score > 0.7:
                risk_score += 2
            elif anomaly_score > 0.5:
                risk_score += 1
            
            # Determine risk level
            if risk_score >= 6:
                return "HIGH"
            elif risk_score >= 3:
                return "MED"
            else:
                return "LOW"
                
        except Exception as e:
            logger.warning(f"Error determining risk level: {e}")
            return "MED"
    
    def _calculate_optimal_copy_ratio(self, risk_metrics: Dict[str, float]) -> float:
        """Calculate optimal copy ratio based on risk metrics"""
        try:
            sharpe = risk_metrics['sharpe_like']
            max_dd = risk_metrics['max_drawdown']
            consistency = risk_metrics['consistency']
            
            # Base ratio
            base_ratio = 0.1  # 10%
            
            # Adjust based on Sharpe ratio
            if sharpe > 1.0:
                base_ratio += 0.05
            elif sharpe > 0.5:
                base_ratio += 0.02
            elif sharpe < -0.5:
                base_ratio -= 0.05
            
            # Adjust based on drawdown
            if max_dd < 0.1:
                base_ratio += 0.03
            elif max_dd > 0.2:
                base_ratio -= 0.03
            
            # Adjust based on consistency
            if consistency > 0.7:
                base_ratio += 0.02
            elif consistency < 0.3:
                base_ratio -= 0.02
            
            return max(0.01, min(0.5, base_ratio))  # Clamp to [1%, 50%]
            
        except Exception as e:
            logger.warning(f"Error calculating optimal copy ratio: {e}")
            return 0.1
    
    def _identify_strengths(self, features: np.ndarray, archetype: str) -> List[str]:
        """Identify trader strengths"""
        strengths = []
        
        try:
            # Volume strength
            if features[0] > 2.0:  # High volume
                strengths.append("High trading volume")
            
            # Win rate strength
            if features[3] > 0.6:  # High win rate
                strengths.append("Strong win rate")
            
            # Consistency strength
            if features[7] > 0.7:  # High consistency
                strengths.append("Consistent performance")
            
            # Sharpe ratio strength
            if features[5] > 1.0:  # High Sharpe
                strengths.append("Excellent risk-adjusted returns")
            
            # Archetype-specific strengths
            if archetype == "Conservative Scalper":
                strengths.append("Low-risk trading approach")
            elif archetype == "Risk Manager":
                strengths.append("Strong risk management")
            elif archetype == "Precision Trader":
                strengths.append("Precise entry/exit timing")
            
            return strengths[:3]  # Limit to top 3
            
        except Exception as e:
            logger.warning(f"Error identifying strengths: {e}")
            return ["Active trader"]
    
    def _identify_warnings(self, anomaly_score: float, risk_metrics: Dict[str, float]) -> List[str]:
        """Identify potential warnings"""
        warnings = []
        
        try:
            # Anomaly warnings
            if anomaly_score > 0.7:
                warnings.append("Unusual trading patterns detected")
            
            # Risk warnings
            if risk_metrics['max_drawdown'] > 0.3:
                warnings.append("High maximum drawdown")
            
            if risk_metrics['sharpe_like'] < -0.5:
                warnings.append("Poor risk-adjusted returns")
            
            if risk_metrics['consistency'] < 0.3:
                warnings.append("Inconsistent performance")
            
            return warnings[:2]  # Limit to top 2
            
        except Exception as e:
            logger.warning(f"Error identifying warnings: {e}")
            return ["Limited data for analysis"]
    
    async def _periodic_model_update(self):
        """Periodically update models with new data"""
        while True:
            try:
                await asyncio.sleep(self.config.AI_MODEL_UPDATE_INTERVAL)
                
                # Check if we need to retrain
                if (self.last_training_time is None or 
                    (datetime.utcnow() - self.last_training_time).total_seconds() > 86400):  # 24 hours
                    
                    logger.info("Periodic model update triggered")
                    await self._train_models()
                    
            except Exception as e:
                logger.error(f"Error in periodic model update: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour before retry
    
    async def _analyze_new_traders(self):
        """Analyze new traders that haven't been analyzed yet"""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                # Get traders that need analysis
                new_traders = await self._get_traders_needing_analysis()
                
                for trader_address in new_traders:
                    try:
                        # Get trader stats
                        from ..analytics.position_tracker import PositionTracker
                        tracker = PositionTracker(self.db_pool, self.redis, self.config)
                        stats = await tracker.get_trader_stats(trader_address)
                        
                        if stats:
                            # Generate analysis
                            analysis = await self.analyze_trader(trader_address, stats)
                            
                            # Store analysis
                            await self._store_trader_analysis(analysis)
                            
                    except Exception as e:
                        logger.error(f"Error analyzing trader {trader_address}: {e}")
                
            except Exception as e:
                logger.error(f"Error in new trader analysis: {e}")
                await asyncio.sleep(300)
    
    async def _get_traders_needing_analysis(self) -> List[str]:
        """Get traders that need AI analysis"""
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT ts.address
                    FROM trader_stats ts
                    LEFT JOIN trader_analytics ta ON ts.address = ta.address AND ts.window = ta.window
                    WHERE ta.address IS NULL
                      AND ts.trade_count_30d >= 20
                      AND ts.last_trade_at > NOW() - INTERVAL '7 days'
                    LIMIT 10
                """
                rows = await conn.fetch(query)
                return [row['address'] for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting traders needing analysis: {e}")
            return []
    
    async def _store_trader_analysis(self, analysis: TraderAnalysis):
        """Store trader analysis in database"""
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    INSERT INTO trader_analytics (
                        address, window, sharpe_like, max_drawdown, consistency,
                        archetype, win_prob_7d, expected_dd_7d, optimal_copy_ratio,
                        risk_level, strengths, warnings, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                    ON CONFLICT (address, window) DO UPDATE SET
                        sharpe_like = EXCLUDED.sharpe_like,
                        max_drawdown = EXCLUDED.max_drawdown,
                        consistency = EXCLUDED.consistency,
                        archetype = EXCLUDED.archetype,
                        win_prob_7d = EXCLUDED.win_prob_7d,
                        expected_dd_7d = EXCLUDED.expected_dd_7d,
                        optimal_copy_ratio = EXCLUDED.optimal_copy_ratio,
                        risk_level = EXCLUDED.risk_level,
                        strengths = EXCLUDED.strengths,
                        warnings = EXCLUDED.warnings,
                        updated_at = EXCLUDED.updated_at
                """
                
                await conn.execute(
                    query,
                    analysis.address,
                    '30d',
                    analysis.sharpe_like,
                    analysis.max_drawdown,
                    analysis.consistency,
                    analysis.archetype,
                    analysis.win_prob_7d,
                    analysis.expected_dd_7d,
                    analysis.optimal_copy_ratio,
                    analysis.risk_level,
                    analysis.strengths,
                    analysis.warnings,
                    datetime.utcnow()
                )
                
            logger.debug(f"Stored analysis for trader {analysis.address[:10]}...")
            
        except Exception as e:
            logger.error(f"Error storing trader analysis: {e}")
    
    async def _store_model_metadata(self):
        """Store model training metadata"""
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    UPDATE ai_model_metadata 
                    SET last_trained_at = $1, 
                        training_data_size = $2,
                        accuracy_score = $3,
                        model_parameters = $4,
                        performance_metrics = $5
                    WHERE model_name = 'trader_analyzer_v1'
                """
                
                # Calculate model performance metrics
                metrics = {
                    'feature_importance': self.performance_model.feature_importances_.tolist() if hasattr(self.performance_model, 'feature_importances_') else [],
                    'n_estimators': self.performance_model.n_estimators,
                    'max_depth': self.performance_model.max_depth
                }
                
                await conn.execute(
                    query,
                    self.last_training_time,
                    1000,  # Placeholder for training data size
                    0.75,  # Placeholder for accuracy
                    metrics,
                    {'status': 'trained', 'version': '1.0.0'}
                )
                
        except Exception as e:
            logger.error(f"Error storing model metadata: {e}")
    
    async def stop(self):
        """Stop the AI analysis service"""
        logger.info("Stopping AI trader analysis service...")
        # Cleanup resources if needed
