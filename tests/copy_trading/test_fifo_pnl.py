"""
Test FIFO PnL Calculation
Tests the position tracker's FIFO PnL calculation logic
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from src.analytics.position_tracker import PositionTracker

class TestFIFOPnL:
    def test_simple_position_close(self):
        """Test basic FIFO PnL calculation"""
        trades = [
            {'event_type': 'OPENED', 'pair_symbol': 'BTC-USD', 'size': 1.0, 'price': 50000, 'is_long': True, 'timestamp': datetime(2024, 1, 1)},
            {'event_type': 'CLOSED', 'pair_symbol': 'BTC-USD', 'size': 1.0, 'price': 55000, 'is_long': True, 'timestamp': datetime(2024, 1, 2), 'fee': 10}
        ]
        
        tracker = PositionTracker(None, None, None)
        pnl = tracker._calculate_fifo_pnl(trades)
        
        expected_pnl = 1.0 * (55000 - 50000) / 50000 - 10  # 10% gain minus fee
        assert abs(pnl - expected_pnl) < 0.01
    
    def test_partial_position_close(self):
        """Test partial position closing"""
        trades = [
            {'event_type': 'OPENED', 'pair_symbol': 'ETH-USD', 'size': 2.0, 'price': 3000, 'is_long': True, 'timestamp': datetime(2024, 1, 1)},
            {'event_type': 'CLOSED', 'pair_symbol': 'ETH-USD', 'size': 1.0, 'price': 3300, 'is_long': True, 'timestamp': datetime(2024, 1, 2), 'fee': 5}
        ]
        
        tracker = PositionTracker(None, None, None)
        pnl = tracker._calculate_fifo_pnl(trades)
        
        expected_pnl = 1.0 * (3300 - 3000) / 3000 - 5  # 10% gain on half position minus fee
        assert abs(pnl - expected_pnl) < 0.01
    
    def test_multiple_lots_fifo(self):
        """Test FIFO with multiple lots"""
        trades = [
            {'event_type': 'OPENED', 'pair_symbol': 'SOL-USD', 'size': 1.0, 'price': 100, 'is_long': True, 'timestamp': datetime(2024, 1, 1)},
            {'event_type': 'OPENED', 'pair_symbol': 'SOL-USD', 'size': 1.0, 'price': 120, 'is_long': True, 'timestamp': datetime(2024, 1, 2)},
            {'event_type': 'CLOSED', 'pair_symbol': 'SOL-USD', 'size': 1.5, 'price': 110, 'is_long': True, 'timestamp': datetime(2024, 1, 3), 'fee': 2}
        ]
        
        tracker = PositionTracker(None, None, None)
        pnl = tracker._calculate_fifo_pnl(trades)
        
        # First lot: 1.0 * (110 - 100) / 100 = 0.1
        # Second lot (partial): 0.5 * (110 - 120) / 120 = -0.0417
        expected_pnl = 0.1 + (-0.0417) - 2
        assert abs(pnl - expected_pnl) < 0.01
    
    def test_short_position_fifo(self):
        """Test FIFO with short positions"""
        trades = [
            {'event_type': 'OPENED', 'pair_symbol': 'BTC-USD', 'size': 1.0, 'price': 50000, 'is_long': False, 'timestamp': datetime(2024, 1, 1)},
            {'event_type': 'CLOSED', 'pair_symbol': 'BTC-USD', 'size': 1.0, 'price': 45000, 'is_long': False, 'timestamp': datetime(2024, 1, 2), 'fee': 10}
        ]
        
        tracker = PositionTracker(None, None, None)
        pnl = tracker._calculate_fifo_pnl(trades)
        
        # Short position: 1.0 * (50000 - 45000) / 50000 = 0.1 (10% gain)
        expected_pnl = 0.1 - 10
        assert abs(pnl - expected_pnl) < 0.01
    
    def test_mixed_long_short_positions(self):
        """Test FIFO with mixed long and short positions"""
        trades = [
            {'event_type': 'OPENED', 'pair_symbol': 'ETH-USD', 'size': 1.0, 'price': 3000, 'is_long': True, 'timestamp': datetime(2024, 1, 1)},
            {'event_type': 'OPENED', 'pair_symbol': 'ETH-USD', 'size': 1.0, 'price': 3200, 'is_long': False, 'timestamp': datetime(2024, 1, 2)},
            {'event_type': 'CLOSED', 'pair_symbol': 'ETH-USD', 'size': 1.0, 'price': 3100, 'is_long': True, 'timestamp': datetime(2024, 1, 3), 'fee': 5},
            {'event_type': 'CLOSED', 'pair_symbol': 'ETH-USD', 'size': 1.0, 'price': 3100, 'is_long': False, 'timestamp': datetime(2024, 1, 4), 'fee': 5}
        ]
        
        tracker = PositionTracker(None, None, None)
        pnl = tracker._calculate_fifo_pnl(trades)
        
        # Long position: 1.0 * (3100 - 3000) / 3000 = 0.0333
        # Short position: 1.0 * (3200 - 3100) / 3200 = 0.03125
        expected_pnl = 0.0333 + 0.03125 - 10  # Total fees
        assert abs(pnl - expected_pnl) < 0.01
    
    def test_empty_trades_list(self):
        """Test FIFO calculation with empty trades list"""
        tracker = PositionTracker(None, None, None)
        pnl = tracker._calculate_fifo_pnl([])
        assert pnl == 0.0
    
    def test_only_opened_trades(self):
        """Test FIFO calculation with only opened trades (no closes)"""
        trades = [
            {'event_type': 'OPENED', 'pair_symbol': 'BTC-USD', 'size': 1.0, 'price': 50000, 'is_long': True, 'timestamp': datetime(2024, 1, 1)},
            {'event_type': 'OPENED', 'pair_symbol': 'BTC-USD', 'size': 1.0, 'price': 51000, 'is_long': True, 'timestamp': datetime(2024, 1, 2)}
        ]
        
        tracker = PositionTracker(None, None, None)
        pnl = tracker._calculate_fifo_pnl(trades)
        assert pnl == 0.0  # No closed trades, no realized PnL
    
    def test_large_dataset_performance(self):
        """Test FIFO calculation performance with large dataset"""
        trades = []
        
        # Generate 1000 trades
        for i in range(1000):
            if i % 3 == 0:  # Every 3rd trade is an open
                trades.append({
                    'event_type': 'OPENED',
                    'pair_symbol': 'BTC-USD',
                    'size': 0.1,
                    'price': 50000 + (i % 100) * 100,
                    'is_long': True,
                    'timestamp': datetime(2024, 1, 1) + timedelta(minutes=i),
                    'fee': 1
                })
            else:  # Close trades
                trades.append({
                    'event_type': 'CLOSED',
                    'pair_symbol': 'BTC-USD',
                    'size': 0.1,
                    'price': 50000 + (i % 100) * 100 + 500,
                    'is_long': True,
                    'timestamp': datetime(2024, 1, 1) + timedelta(minutes=i),
                    'fee': 1
                })
        
        tracker = PositionTracker(None, None, None)
        
        import time
        start_time = time.time()
        pnl = tracker._calculate_fifo_pnl(trades)
        elapsed = time.time() - start_time
        
        # Should process 1000 trades in under 1 second
        assert elapsed < 1.0
        assert isinstance(pnl, float)
    
    def test_win_rate_calculation(self):
        """Test win rate calculation"""
        trades = [
            # Winning trades
            {'event_type': 'OPENED', 'pair_symbol': 'BTC-USD', 'size': 1.0, 'price': 50000, 'is_long': True, 'timestamp': datetime(2024, 1, 1)},
            {'event_type': 'CLOSED', 'pair_symbol': 'BTC-USD', 'size': 1.0, 'price': 55000, 'is_long': True, 'timestamp': datetime(2024, 1, 2), 'fee': 10},
            
            # Losing trade
            {'event_type': 'OPENED', 'pair_symbol': 'ETH-USD', 'size': 1.0, 'price': 3000, 'is_long': True, 'timestamp': datetime(2024, 1, 3)},
            {'event_type': 'CLOSED', 'pair_symbol': 'ETH-USD', 'size': 1.0, 'price': 2700, 'is_long': True, 'timestamp': datetime(2024, 1, 4), 'fee': 10},
            
            # Another winning trade
            {'event_type': 'OPENED', 'pair_symbol': 'SOL-USD', 'size': 1.0, 'price': 100, 'is_long': True, 'timestamp': datetime(2024, 1, 5)},
            {'event_type': 'CLOSED', 'pair_symbol': 'SOL-USD', 'size': 1.0, 'price': 110, 'is_long': True, 'timestamp': datetime(2024, 1, 6), 'fee': 10}
        ]
        
        tracker = PositionTracker(None, None, None)
        win_rate = tracker._calculate_win_rate(trades)
        
        # Should be 2/3 = 0.667 (66.7%)
        assert abs(win_rate - 0.667) < 0.01
    
    def test_maker_ratio_calculation(self):
        """Test maker ratio calculation"""
        trades = [
            {'event_type': 'OPENED', 'pair_symbol': 'BTC-USD', 'size': 1.0, 'price': 50000, 'is_long': True, 'timestamp': datetime(2024, 1, 1)},
            {'event_type': 'OPENED', 'pair_symbol': 'BTC-USD', 'size': 1.0, 'price': 50000, 'is_long': True, 'timestamp': datetime(2024, 1, 2)},
            {'event_type': 'OPENED', 'pair_symbol': 'BTC-USD', 'size': 1.0, 'price': 50000, 'is_long': True, 'timestamp': datetime(2024, 1, 3)},
        ]
        
        tracker = PositionTracker(None, None, None)
        maker_ratio = tracker._calculate_maker_ratio(trades)
        
        # With consistent sizing, should have high maker ratio
        assert maker_ratio is not None
        assert 0.0 <= maker_ratio <= 1.0
    
    def test_leverage_consistency(self):
        """Test leverage consistency calculation"""
        trades = [
            {'event_type': 'OPENED', 'pair_symbol': 'BTC-USD', 'size': 1.0, 'price': 50000, 'is_long': True, 'leverage': 10, 'timestamp': datetime(2024, 1, 1)},
            {'event_type': 'OPENED', 'pair_symbol': 'BTC-USD', 'size': 1.0, 'price': 50000, 'is_long': True, 'leverage': 10, 'timestamp': datetime(2024, 1, 2)},
            {'event_type': 'OPENED', 'pair_symbol': 'BTC-USD', 'size': 1.0, 'price': 50000, 'is_long': True, 'leverage': 10, 'timestamp': datetime(2024, 1, 3)},
        ]
        
        tracker = PositionTracker(None, None, None)
        consistency = tracker._calculate_leverage_consistency(trades)
        
        # With consistent leverage, should have high consistency
        assert consistency == 1.0
    
    def test_hold_time_calculation(self):
        """Test average hold time calculation"""
        trades = [
            {'event_type': 'OPENED', 'pair_symbol': 'BTC-USD', 'size': 1.0, 'price': 50000, 'is_long': True, 'timestamp': datetime(2024, 1, 1, 10, 0)},
            {'event_type': 'CLOSED', 'pair_symbol': 'BTC-USD', 'size': 1.0, 'price': 55000, 'is_long': True, 'timestamp': datetime(2024, 1, 1, 12, 0)},  # 2 hours
            {'event_type': 'OPENED', 'pair_symbol': 'ETH-USD', 'size': 1.0, 'price': 3000, 'is_long': True, 'timestamp': datetime(2024, 1, 2, 10, 0)},
            {'event_type': 'CLOSED', 'pair_symbol': 'ETH-USD', 'size': 1.0, 'price': 3300, 'is_long': True, 'timestamp': datetime(2024, 1, 2, 16, 0)},  # 6 hours
        ]
        
        tracker = PositionTracker(None, None, None)
        avg_hold_time = tracker._calculate_avg_hold_time(trades)
        
        # Average of 2 and 6 hours = 4 hours
        assert abs(avg_hold_time - 4.0) < 0.1
