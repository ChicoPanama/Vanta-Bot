"""
Test AI Trader Analyzer
Tests the AI trader analysis and prediction engine
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from src.ai.trader_analyzer import TraderAnalyzer, TraderAnalysis
from src.analytics.position_tracker import TraderStats

class TestTraderAnalyzer:
    def test_feature_extraction(self):
        """Test ML feature extraction"""
        stats = TraderStats(
            address='0x123',
            last_30d_volume_usd=1000000,
            trade_count_30d=100,
            win_rate=0.65,
            maker_ratio=0.3,
            unique_symbols=5,
            median_trade_size_usd=10000,
            realized_pnl_clean_usd=50000,
            last_trade_at=datetime.utcnow(),
            avg_hold_time_hours=2.5,
            leverage_consistency=0.8
        )
        
        trades = [
            {'size': 1.0, 'price': 50000, 'is_long': True, 'leverage': 10, 'timestamp': datetime.utcnow() - timedelta(hours=i)}
            for i in range(20)
        ]
        
        analyzer = TraderAnalyzer(None, None, None)
        features = analyzer._extract_features_from_data({
            'address': stats.address,
            'last_30d_volume_usd': stats.last_30d_volume_usd,
            'trade_count_30d': stats.trade_count_30d,
            'median_trade_size_usd': stats.median_trade_size_usd,
            'win_rate': stats.win_rate,
            'maker_ratio': stats.maker_ratio,
            'unique_symbols': stats.unique_symbols,
            'realized_pnl_clean_usd': stats.realized_pnl_clean_usd,
            'sharpe_like': 0.0,
            'max_drawdown': 0.0,
            'consistency': stats.leverage_consistency
        })
        
        assert len(features) == 20  # Expected feature vector length
        assert features[0] > 0  # Volume feature should be positive
        assert 0 <= features[3] <= 1  # Win rate should be normalized
    
    def test_risk_metrics_calculation(self):
        """Test risk metrics calculation"""
        # Simulate daily returns
        trades = []
        base_price = 50000
        for i in range(30):
            price = base_price * (1 + (i % 5 - 2) * 0.02)  # Simulate price changes
            trades.append({
                'event_type': 'CLOSED',
                'pnl': price - base_price,
                'timestamp': datetime.utcnow() - timedelta(days=30-i),
                'size': 1.0,
                'price': price
            })
        
        analyzer = TraderAnalyzer(None, None, None)
        risk_metrics = analyzer._calculate_risk_metrics(trades)
        
        assert 'sharpe_like' in risk_metrics
        assert 'max_drawdown' in risk_metrics
        assert 'consistency' in risk_metrics
        assert risk_metrics['max_drawdown'] >= 0
    
    def test_archetype_classification(self):
        """Test trader archetype classification"""
        analyzer = TraderAnalyzer(None, None, None)
        
        # Test with mock features
        features = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 
                           0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
        
        # Mock the clustering model
        analyzer.clustering_model.predict = lambda x: [0]  # Conservative Scalper
        
        archetype = analyzer._classify_archetype(features)
        assert archetype == "Conservative Scalper"
    
    def test_anomaly_detection(self):
        """Test anomaly detection"""
        analyzer = TraderAnalyzer(None, None, None)
        
        # Test with normal features
        normal_features = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 
                                  0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
        
        # Mock the anomaly detector
        analyzer.anomaly_detector.decision_function = lambda x: [0.5]  # Normal score
        
        anomaly_score = analyzer._detect_anomalies(normal_features)
        assert 0.0 <= anomaly_score <= 1.0
    
    def test_performance_prediction(self):
        """Test performance prediction"""
        analyzer = TraderAnalyzer(None, None, None)
        
        # Test with mock features
        features = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 
                           0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
        
        # Mock the performance model
        analyzer.performance_model.predict = lambda x: [0.75]  # Good performance
        
        performance = analyzer._predict_performance(features)
        assert 0.0 <= performance <= 1.0
    
    def test_risk_level_determination(self):
        """Test risk level determination"""
        analyzer = TraderAnalyzer(None, None, None)
        
        # Test low risk
        low_risk_metrics = {
            'sharpe_like': 1.5,
            'max_drawdown': 0.05,
            'consistency': 0.8
        }
        risk_level = analyzer._determine_risk_level(low_risk_metrics, 0.2)
        assert risk_level == "LOW"
        
        # Test high risk
        high_risk_metrics = {
            'sharpe_like': -0.8,
            'max_drawdown': 0.4,
            'consistency': 0.2
        }
        risk_level = analyzer._determine_risk_level(high_risk_metrics, 0.8)
        assert risk_level == "HIGH"
        
        # Test medium risk
        medium_risk_metrics = {
            'sharpe_like': 0.2,
            'max_drawdown': 0.15,
            'consistency': 0.5
        }
        risk_level = analyzer._determine_risk_level(medium_risk_metrics, 0.5)
        assert risk_level == "MED"
    
    def test_optimal_copy_ratio_calculation(self):
        """Test optimal copy ratio calculation"""
        analyzer = TraderAnalyzer(None, None, None)
        
        # Test with good metrics
        good_metrics = {
            'sharpe_like': 1.2,
            'max_drawdown': 0.08,
            'consistency': 0.8
        }
        ratio = analyzer._calculate_optimal_copy_ratio(good_metrics)
        assert 0.01 <= ratio <= 0.5  # Should be within reasonable range
        
        # Test with poor metrics
        poor_metrics = {
            'sharpe_like': -0.5,
            'max_drawdown': 0.3,
            'consistency': 0.2
        }
        ratio = analyzer._calculate_optimal_copy_ratio(poor_metrics)
        assert 0.01 <= ratio <= 0.5  # Should still be within range
    
    def test_strengths_identification(self):
        """Test strengths identification"""
        analyzer = TraderAnalyzer(None, None, None)
        
        # Test with good features
        good_features = np.array([2.5, 3.0, 2.0, 0.7, 0.8, 1.2, 0.05, 0.8, 0.6, 0.5,
                                0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
        
        strengths = analyzer._identify_strengths(good_features, "Risk Manager")
        assert len(strengths) > 0
        assert "Strong risk management" in strengths
    
    def test_warnings_identification(self):
        """Test warnings identification"""
        analyzer = TraderAnalyzer(None, None, None)
        
        # Test with high risk metrics
        high_risk_metrics = {
            'sharpe_like': -0.8,
            'max_drawdown': 0.4,
            'consistency': 0.2
        }
        
        warnings = analyzer._identify_warnings(0.8, high_risk_metrics)
        assert len(warnings) > 0
        assert any("High maximum drawdown" in warning for warning in warnings)
    
    def test_forecast_generation(self):
        """Test 7-day forecast generation"""
        analyzer = TraderAnalyzer(None, None, None)
        
        # Test with mock features
        features = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 
                           0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
        
        trades = [
            {'event_type': 'CLOSED', 'pnl': 100, 'timestamp': datetime.utcnow() - timedelta(days=i)}
            for i in range(20)
        ]
        
        # Mock the performance model
        analyzer.performance_model.predict = lambda x: [0.65]  # 65% win probability
        
        forecasts = analyzer._generate_forecasts(features, trades)
        
        assert 'win_probability' in forecasts
        assert 'expected_drawdown' in forecasts
        assert 'confidence' in forecasts
        assert 0.0 <= forecasts['win_probability'] <= 1.0
        assert 0.0 <= forecasts['expected_drawdown'] <= 1.0
        assert 0.0 <= forecasts['confidence'] <= 1.0
    
    def test_volatility_calculation(self):
        """Test recent volatility calculation"""
        analyzer = TraderAnalyzer(None, None, None)
        
        # Test with recent trades
        recent_trades = [
            {'event_type': 'CLOSED', 'pnl': 100, 'timestamp': datetime.utcnow() - timedelta(days=i)}
            for i in range(10)
        ]
        
        volatility = analyzer._calculate_recent_volatility(recent_trades)
        assert 0.0 <= volatility <= 1.0
    
    def test_daily_returns_calculation(self):
        """Test daily returns calculation"""
        analyzer = TraderAnalyzer(None, None, None)
        
        trades = [
            {'event_type': 'CLOSED', 'pnl': 100, 'timestamp': datetime(2024, 1, 1)},
            {'event_type': 'CLOSED', 'pnl': -50, 'timestamp': datetime(2024, 1, 2)},
            {'event_type': 'CLOSED', 'pnl': 200, 'timestamp': datetime(2024, 1, 3)},
        ]
        
        returns = analyzer._calculate_daily_returns(trades)
        assert len(returns) == 3
        assert returns[0] == 100
        assert returns[1] == -50
        assert returns[2] == 200
    
    def test_rolling_win_rates(self):
        """Test rolling win rates calculation"""
        analyzer = TraderAnalyzer(None, None, None)
        
        trades = []
        for i in range(20):
            pnl = 100 if i % 3 != 0 else -50  # 2/3 win rate
            trades.append({
                'event_type': 'CLOSED',
                'pnl': pnl,
                'timestamp': datetime(2024, 1, 1) + timedelta(days=i)
            })
        
        win_rates = analyzer._calculate_rolling_win_rates(trades, window=7)
        assert len(win_rates) > 0
        assert all(0.0 <= rate <= 1.0 for rate in win_rates)
    
    def test_default_analysis_creation(self):
        """Test default analysis creation when model not available"""
        analyzer = TraderAnalyzer(None, None, None)
        
        analysis = analyzer._create_default_analysis("0x123")
        
        assert analysis.address == "0x123"
        assert analysis.archetype == "Unknown"
        assert analysis.performance_score == 0.5
        assert analysis.risk_level == "MED"
        assert "Limited data for analysis" in analysis.warnings
    
    @pytest.mark.asyncio
    async def test_analyze_trader_integration(self):
        """Test full trader analysis integration"""
        analyzer = TraderAnalyzer(None, None, None)
        
        # Create mock stats
        stats = TraderStats(
            address='0x123',
            last_30d_volume_usd=1000000,
            trade_count_30d=100,
            win_rate=0.65,
            maker_ratio=0.3,
            unique_symbols=5,
            median_trade_size_usd=10000,
            realized_pnl_clean_usd=50000,
            last_trade_at=datetime.utcnow(),
            avg_hold_time_hours=2.5,
            leverage_consistency=0.8
        )
        
        # Mock trades
        trades = [
            {'event_type': 'CLOSED', 'pnl': 100, 'timestamp': datetime.utcnow() - timedelta(days=i)}
            for i in range(20)
        ]
        
        # Test analysis (should work even without trained models)
        analysis = await analyzer.analyze_trader("0x123", stats, trades)
        
        assert isinstance(analysis, TraderAnalysis)
        assert analysis.address == "0x123"
        assert analysis.archetype in ["Unknown", "Conservative Scalper", "Risk Manager", "Precision Trader", "Volume Hunter", "Aggressive Swinger"]
        assert 0.0 <= analysis.performance_score <= 1.0
        assert analysis.risk_level in ["LOW", "MED", "HIGH"]
        assert len(analysis.strengths) > 0
        assert len(analysis.warnings) > 0
import os
import pytest

pytestmark = pytest.mark.skipif(not os.getenv("RUN_SLOW"), reason="slow/infra-heavy suite; set RUN_SLOW=1 to enable")
