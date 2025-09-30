"""
AI Trader Analysis Engine for Vanta Bot
Uses ML models to assess trader performance, risk, and classify archetypes
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from ..analytics.position_tracker import TraderStats

logger = logging.getLogger(__name__)


@dataclass
class TraderAnalysis:
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
    strengths: list[str]
    warnings: list[str]


class TraderAnalyzer:
    """AI-powered trader analysis and classification"""

    def __init__(self, config):
        self.config = config

        # ML Models
        self.performance_model = RandomForestRegressor(
            n_estimators=100, max_depth=10, random_state=42, n_jobs=-1
        )
        self.anomaly_detector = IsolationForest(
            contamination=0.1, random_state=42, n_jobs=-1
        )
        self.clustering_model = KMeans(n_clusters=5, random_state=42, n_init=10)
        self.scaler = StandardScaler()

        # Trader archetypes
        self.archetypes = {
            0: "Conservative Scalper",
            1: "Aggressive Swinger",
            2: "Risk Manager",
            3: "Volume Hunter",
            4: "Precision Trader",
        }

        # Model training state
        self.is_trained = False
        self.last_training_time = None

    async def analyze_trader(
        self, address: str, stats: TraderStats, trades: list[dict]
    ) -> TraderAnalysis:
        """Generate comprehensive AI analysis for a trader"""
        try:
            # Extract features
            features = self._extract_features(stats, trades)

            if features is None:
                return self._create_default_analysis(address)

            # Ensure model is trained
            if not self.is_trained:
                await self._train_models()

            # Performance prediction
            performance_score = self._predict_performance(features)

            # Anomaly detection
            anomaly_score = self._detect_anomalies(features)

            # Archetype classification
            archetype = self._classify_archetype(features)

            # Risk metrics
            risk_metrics = self._calculate_risk_metrics(trades)

            # 7-day forecasts
            forecasts = self._generate_forecasts(features, trades)

            # Generate insights
            strengths = self._identify_strengths(features, archetype)
            warnings = self._identify_warnings(anomaly_score, risk_metrics)

            return TraderAnalysis(
                address=address,
                archetype=self.archetypes.get(archetype, "Unknown"),
                performance_score=performance_score,
                anomaly_score=anomaly_score,
                risk_level=self._determine_risk_level(risk_metrics),
                sharpe_like=risk_metrics["sharpe_like"],
                max_drawdown=risk_metrics["max_drawdown"],
                consistency=risk_metrics["consistency"],
                win_prob_7d=forecasts["win_probability"],
                expected_dd_7d=forecasts["expected_drawdown"],
                optimal_copy_ratio=self._calculate_optimal_copy_ratio(risk_metrics),
                strengths=strengths,
                warnings=warnings,
            )

        except Exception as e:
            logger.error(f"Error analyzing trader {address}: {e}")
            return self._create_default_analysis(address)

    def _extract_features(
        self, stats: TraderStats, trades: list[dict]
    ) -> Optional[np.ndarray]:
        """Extract ML features from trader data"""
        try:
            if not trades:
                return np.zeros(20)  # Default feature vector

            # Basic stats features (log-normalized)
            volume_normalized = np.log1p(max(stats.last_30d_volume_usd, 1))
            trade_count_normalized = np.log1p(max(stats.trade_count_30d, 1))
            median_size_normalized = np.log1p(max(stats.median_trade_size_usd, 1))

            # Trading pattern features
            hold_times = self._calculate_hold_times(trades)
            avg_hold_time = np.mean(hold_times) if hold_times else 0
            hold_time_std = np.std(hold_times) if len(hold_times) > 1 else 0

            # Leverage analysis
            leverages = [trade.get("leverage", 1) for trade in trades]
            avg_leverage = np.mean(leverages) if leverages else 1
            leverage_consistency = (
                1 - (np.std(leverages) / max(np.mean(leverages), 1)) if leverages else 0
            )

            # Symbol diversity
            symbol_entropy = self._calculate_symbol_entropy(trades)

            # Time pattern features
            hourly_distribution = self._analyze_time_patterns(trades)

            # Direction bias
            long_ratio = sum(1 for t in trades if t.get("is_long", True)) / len(trades)

            # Size scaling pattern
            size_consistency = self._analyze_size_consistency(trades)

            # Win rate and other stats
            win_rate = stats.win_rate
            maker_ratio = stats.maker_ratio or 0.5
            unique_symbols_ratio = stats.unique_symbols / max(len(trades), 1)

            return np.array(
                [
                    volume_normalized,
                    trade_count_normalized,
                    median_size_normalized,
                    win_rate,
                    maker_ratio,
                    avg_hold_time,
                    hold_time_std,
                    avg_leverage,
                    leverage_consistency,
                    symbol_entropy,
                    long_ratio,
                    size_consistency,
                    *hourly_distribution[:6],  # Top 6 hour preferences
                    unique_symbols_ratio,
                    stats.realized_pnl_clean_usd
                    / max(stats.last_30d_volume_usd, 1),  # ROI
                ]
            )

        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            return None

    def _calculate_hold_times(self, trades: list[dict]) -> list[float]:
        """Calculate hold times for trades"""
        hold_times = []

        # Group trades by pair and direction to calculate hold times
        positions = {}

        for trade in sorted(trades, key=lambda x: x["timestamp"]):
            key = (trade["pair"], trade["is_long"])

            if trade["event_type"] == "OPENED":
                if key not in positions:
                    positions[key] = []
                positions[key].append(trade["timestamp"])

            elif (
                trade["event_type"] == "CLOSED" and key in positions and positions[key]
            ):
                open_time = positions[key].pop(0)
                hold_time = (
                    trade["timestamp"] - open_time
                ).total_seconds() / 3600  # hours
                hold_times.append(hold_time)

        return hold_times

    def _calculate_symbol_entropy(self, trades: list[dict]) -> float:
        """Calculate symbol diversity entropy"""
        if not trades:
            return 0.0

        symbols = [trade["pair"] for trade in trades]
        unique_symbols, counts = np.unique(symbols, return_counts=True)
        probabilities = counts / len(symbols)

        # Calculate Shannon entropy
        entropy = -np.sum(probabilities * np.log2(probabilities + 1e-10))
        return entropy

    def _analyze_time_patterns(self, trades: list[dict]) -> list[float]:
        """Analyze hourly trading patterns"""
        hourly_counts = [0] * 24

        for trade in trades:
            hour = trade["timestamp"].hour
            hourly_counts[hour] += 1

        # Normalize to probabilities
        total_trades = sum(hourly_counts)
        if total_trades > 0:
            hourly_probs = [count / total_trades for count in hourly_counts]
        else:
            hourly_probs = [0] * 24

        return hourly_probs

    def _analyze_size_consistency(self, trades: list[dict]) -> float:
        """Analyze consistency of trade sizes"""
        if len(trades) < 2:
            return 0.0

        sizes = [trade["size"] * trade["price"] for trade in trades]
        cv = np.std(sizes) / np.mean(sizes) if np.mean(sizes) > 0 else 1.0

        # Return inverse of coefficient of variation (higher is more consistent)
        return 1.0 / (1.0 + cv)

    def _calculate_risk_metrics(self, trades: list[dict]) -> dict[str, float]:
        """Calculate comprehensive risk metrics"""
        if not trades:
            return {"sharpe_like": 0, "max_drawdown": 0, "consistency": 0}

        try:
            # Calculate daily returns
            daily_returns = self._calculate_daily_returns(trades)

            if not daily_returns:
                return {"sharpe_like": 0, "max_drawdown": 0, "consistency": 0}

            # Sharpe-like ratio (using EWMA)
            returns_series = pd.Series(daily_returns)
            ewma_return = returns_series.ewm(span=10).mean().iloc[-1]
            ewma_vol = returns_series.ewm(span=10).std().iloc[-1]
            sharpe_like = ewma_return / max(ewma_vol, 0.001)

            # Maximum drawdown
            cumulative_returns = np.cumsum(daily_returns)
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdowns = cumulative_returns - running_max
            max_drawdown = abs(np.min(drawdowns))

            # Consistency (win rate stability)
            win_rates_rolling = self._calculate_rolling_win_rates(trades, window=7)
            consistency = (
                1 - np.std(win_rates_rolling) if len(win_rates_rolling) > 1 else 0
            )

            return {
                "sharpe_like": sharpe_like,
                "max_drawdown": max_drawdown,
                "consistency": consistency,
            }

        except Exception as e:
            logger.error(f"Error calculating risk metrics: {e}")
            return {"sharpe_like": 0, "max_drawdown": 0, "consistency": 0}

    def _calculate_daily_returns(self, trades: list[dict]) -> list[float]:
        """Calculate daily returns from trades"""
        # Group trades by date and calculate daily PnL
        daily_pnl = {}

        for trade in trades:
            if trade["event_type"] == "CLOSED":
                date = trade["timestamp"].date()
                pnl = trade.get("pnl", 0)

                if date not in daily_pnl:
                    daily_pnl[date] = 0
                daily_pnl[date] += pnl

        # Convert to list of daily returns
        dates = sorted(daily_pnl.keys())
        returns = []

        for i in range(1, len(dates)):
            prev_pnl = daily_pnl[dates[i - 1]]
            curr_pnl = daily_pnl[dates[i]]

            # Calculate return (simplified)
            if prev_pnl != 0:
                returns.append((curr_pnl - prev_pnl) / abs(prev_pnl))
            else:
                returns.append(0)

        return returns

    def _calculate_rolling_win_rates(
        self, trades: list[dict], window: int = 7
    ) -> list[float]:
        """Calculate rolling win rates"""
        # Group trades by date
        daily_trades = {}

        for trade in trades:
            if trade["event_type"] == "CLOSED":
                date = trade["timestamp"].date()

                if date not in daily_trades:
                    daily_trades[date] = {"wins": 0, "total": 0}

                daily_trades[date]["total"] += 1
                if trade.get("pnl", 0) > 0:
                    daily_trades[date]["wins"] += 1

        # Calculate rolling win rates
        dates = sorted(daily_trades.keys())
        win_rates = []

        for i in range(window, len(dates)):
            window_dates = dates[i - window : i]
            total_trades = sum(daily_trades[d]["total"] for d in window_dates)
            total_wins = sum(daily_trades[d]["wins"] for d in window_dates)

            if total_trades > 0:
                win_rates.append(total_wins / total_trades)

        return win_rates

    def _predict_performance(self, features: np.ndarray) -> float:
        """Predict future performance using trained model"""
        if not self.is_trained:
            return 0.5  # Neutral prediction

        try:
            # Ensure features are properly shaped
            if features.ndim == 1:
                features = features.reshape(1, -1)

            # Scale features
            features_scaled = self.scaler.transform(features)

            # Predict
            prediction = self.performance_model.predict(features_scaled)[0]

            # Ensure prediction is in valid range
            return max(0.0, min(1.0, prediction))

        except Exception as e:
            logger.error(f"Error predicting performance: {e}")
            return 0.5

    def _detect_anomalies(self, features: np.ndarray) -> float:
        """Detect anomalous trading patterns"""
        if not self.is_trained:
            return 0.5  # Neutral score

        try:
            # Ensure features are properly shaped
            if features.ndim == 1:
                features = features.reshape(1, -1)

            # Scale features
            features_scaled = self.scaler.transform(features)

            # Detect anomaly
            anomaly_score = self.anomaly_detector.decision_function(features_scaled)[0]

            # Normalize to 0-1 range
            return max(0.0, min(1.0, (anomaly_score + 1) / 2))

        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            return 0.5

    def _classify_archetype(self, features: np.ndarray) -> int:
        """Classify trader archetype using clustering"""
        if not self.is_trained:
            return 0  # Default archetype

        try:
            # Ensure features are properly shaped
            if features.ndim == 1:
                features = features.reshape(1, -1)

            # Scale features
            features_scaled = self.scaler.transform(features)

            # Classify
            archetype = self.clustering_model.predict(features_scaled)[0]

            return int(archetype)

        except Exception as e:
            logger.error(f"Error classifying archetype: {e}")
            return 0

    def _generate_forecasts(
        self, features: np.ndarray, trades: list[dict]
    ) -> dict[str, float]:
        """Generate 7-day performance forecasts"""
        try:
            if not self.is_trained:
                return {
                    "win_probability": 0.5,
                    "expected_drawdown": 0.05,
                    "confidence": 0.3,
                }

            # Predict next 7-day win probability
            win_prob = self._predict_performance(features)

            # Estimate expected drawdown based on historical volatility
            recent_volatility = self._calculate_recent_volatility(trades)
            expected_dd = min(0.3, recent_volatility * 1.5)  # Cap at 30%

            # Confidence based on data quality
            confidence = 0.7 if len(trades) > 100 else 0.4

            return {
                "win_probability": win_prob,
                "expected_drawdown": expected_dd,
                "confidence": confidence,
            }

        except Exception as e:
            logger.error(f"Error generating forecasts: {e}")
            return {
                "win_probability": 0.5,
                "expected_drawdown": 0.05,
                "confidence": 0.3,
            }

    def _calculate_recent_volatility(self, trades: list[dict]) -> float:
        """Calculate recent volatility from trades"""
        if len(trades) < 10:
            return 0.1  # Default moderate volatility

        try:
            # Get recent trades (last 30 days)
            recent_trades = [
                t
                for t in trades
                if t["timestamp"] > datetime.utcnow() - timedelta(days=30)
            ]

            if len(recent_trades) < 5:
                return 0.1

            # Calculate PnL volatility
            pnls = [
                t.get("pnl", 0) for t in recent_trades if t["event_type"] == "CLOSED"
            ]

            if len(pnls) < 3:
                return 0.1

            return np.std(pnls) / (np.mean(np.abs(pnls)) + 1e-10)

        except Exception as e:
            logger.error(f"Error calculating volatility: {e}")
            return 0.1

    def _determine_risk_level(self, risk_metrics: dict[str, float]) -> str:
        """Determine overall risk level"""
        sharpe = risk_metrics["sharpe_like"]
        max_dd = risk_metrics["max_drawdown"]
        consistency = risk_metrics["consistency"]

        # Risk scoring
        risk_score = 0

        # Sharpe-based scoring
        if sharpe > 1.0:
            risk_score += 1
        elif sharpe < -0.5:
            risk_score -= 2

        # Drawdown-based scoring
        if max_dd > 0.3:
            risk_score -= 2
        elif max_dd < 0.1:
            risk_score += 1

        # Consistency-based scoring
        if consistency > 0.8:
            risk_score += 1
        elif consistency < 0.4:
            risk_score -= 1

        # Determine risk level
        if risk_score >= 2:
            return "LOW"
        elif risk_score >= 0:
            return "MED"
        else:
            return "HIGH"

    def _calculate_optimal_copy_ratio(self, risk_metrics: dict[str, float]) -> float:
        """Calculate optimal copy ratio based on risk metrics"""
        sharpe = risk_metrics["sharpe_like"]
        max_dd = risk_metrics["max_drawdown"]
        consistency = risk_metrics["consistency"]

        # Base ratio
        base_ratio = 0.1  # 10%

        # Adjust based on metrics
        if sharpe > 1.0:
            base_ratio += 0.05
        if max_dd < 0.15:
            base_ratio += 0.05
        if consistency > 0.7:
            base_ratio += 0.05

        # Cap at reasonable limits
        return max(0.05, min(0.3, base_ratio))

    def _identify_strengths(self, features: np.ndarray, archetype: int) -> list[str]:
        """Identify trader strengths"""
        strengths = []

        # Volume strength
        if features[0] > 2.0:  # High volume
            strengths.append("High trading volume")

        # Consistency strength
        if features[11] > 0.7:  # Size consistency
            strengths.append("Consistent position sizing")

        # Diversification strength
        if features[13] > 0.5:  # Symbol diversity
            strengths.append("Well-diversified across symbols")

        # Archetype-specific strengths
        if archetype == 0:  # Conservative Scalper
            strengths.append("Conservative risk management")
        elif archetype == 1:  # Aggressive Swinger
            strengths.append("Strong trend-following ability")
        elif archetype == 2:  # Risk Manager
            strengths.append("Excellent risk control")
        elif archetype == 3:  # Volume Hunter
            strengths.append("High-volume execution")
        elif archetype == 4:  # Precision Trader
            strengths.append("Precise entry/exit timing")

        return strengths[:3]  # Return top 3

    def _identify_warnings(
        self, anomaly_score: float, risk_metrics: dict[str, float]
    ) -> list[str]:
        """Identify potential warnings"""
        warnings = []

        # Anomaly warnings
        if anomaly_score < 0.3:
            warnings.append("Unusual trading patterns detected")

        # Risk warnings
        if risk_metrics["max_drawdown"] > 0.25:
            warnings.append("High historical drawdown")

        if risk_metrics["sharpe_like"] < -0.5:
            warnings.append("Poor risk-adjusted returns")

        if risk_metrics["consistency"] < 0.3:
            warnings.append("Inconsistent performance")

        return warnings[:2]  # Return top 2

    def _create_default_analysis(self, address: str) -> TraderAnalysis:
        """Create default analysis for traders with insufficient data"""
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
            expected_dd_7d=0.1,
            optimal_copy_ratio=0.1,
            strengths=["Insufficient data for analysis"],
            warnings=["Need more trading history"],
        )

    async def _train_models(self):
        """Train ML models on historical data"""
        try:
            logger.info("Training AI models...")

            # Get training data (this would be implemented with actual data)
            # For now, create synthetic training data
            X, y = self._generate_training_data()

            if len(X) < 50:  # Need minimum data for training
                logger.warning("Insufficient training data, using default models")
                return

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)

            # Train performance model
            self.performance_model.fit(X_train_scaled, y_train)

            # Train anomaly detector
            self.anomaly_detector.fit(X_train_scaled)

            # Train clustering model
            self.clustering_model.fit(X_train_scaled)

            # Evaluate models
            y_pred = self.performance_model.predict(X_test_scaled)
            mse = mean_squared_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)

            logger.info(f"Model training completed - MSE: {mse:.4f}, R²: {r2:.4f}")

            self.is_trained = True
            self.last_training_time = datetime.utcnow()

            # Save models
            await self._save_models()

        except Exception as e:
            logger.error(f"Error training models: {e}")

    def _generate_training_data(self) -> tuple[np.ndarray, np.ndarray]:
        """Generate synthetic training data for model training"""
        # In production, this would load real historical trader data
        # For now, generate synthetic data for demonstration

        np.random.seed(42)
        n_samples = 1000
        n_features = 20

        # Generate features
        X = np.random.randn(n_samples, n_features)

        # Generate targets (performance scores)
        # Make it somewhat realistic based on feature combinations
        y = (
            X[:, 0] * 0.3  # Volume impact
            + X[:, 3] * 0.2  # Win rate impact
            + X[:, 11] * 0.2  # Consistency impact
            + X[:, 13] * 0.1  # Diversification impact
            + np.random.randn(n_samples) * 0.2  # Random noise
        )

        # Normalize to 0-1 range
        y = (y - y.min()) / (y.max() - y.min())

        return X, y

    async def _save_models(self):
        """Save trained models to disk"""
        try:
            model_dir = "models"
            import os

            os.makedirs(model_dir, exist_ok=True)

            # Save models
            joblib.dump(self.performance_model, f"{model_dir}/performance_model.pkl")
            joblib.dump(self.anomaly_detector, f"{model_dir}/anomaly_detector.pkl")
            joblib.dump(self.clustering_model, f"{model_dir}/clustering_model.pkl")
            joblib.dump(self.scaler, f"{model_dir}/scaler.pkl")

            logger.info("Models saved successfully")

        except Exception as e:
            logger.error(f"Error saving models: {e}")

    async def _load_models(self):
        """Load pre-trained models from disk"""
        try:
            model_dir = "models"

            # Load models
            self.performance_model = joblib.load(f"{model_dir}/performance_model.pkl")
            self.anomaly_detector = joblib.load(f"{model_dir}/anomaly_detector.pkl")
            self.clustering_model = joblib.load(f"{model_dir}/clustering_model.pkl")
            self.scaler = joblib.load(f"{model_dir}/scaler.pkl")

            self.is_trained = True
            logger.info("Models loaded successfully")

        except Exception as e:
            logger.error(f"Error loading models: {e}")
            self.is_trained = False
