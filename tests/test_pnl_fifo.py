"""
Lightweight smoke test for FIFO PnL calculation
"""
import pytest
from decimal import Decimal
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.services.analytics.fifo_pnl import realized_pnl_fifo

def test_fifo_long_basic():
    """Test basic FIFO calculation for long positions"""
    fills = [
        ("OPEN",  Decimal("1"), Decimal("100"), Decimal("0.1")),
        ("OPEN",  Decimal("1"), Decimal("110"), Decimal("0.1")),
        ("CLOSE", Decimal("1"), Decimal("120"), Decimal("0.1")),
        ("CLOSE", Decimal("1"), Decimal("90"),  Decimal("0.1")),
    ]
    # PnL: (120-100)*1 + (90-110)*1 = 20 - 20 = 0, minus fees 0.4 = -0.4
    assert realized_pnl_fifo(fills) == Decimal("-0.4")

def test_fifo_long_profitable():
    """Test profitable FIFO calculation"""
    fills = [
        ("OPEN",  Decimal("2"), Decimal("100"), Decimal("0.1")),
        ("CLOSE", Decimal("1"), Decimal("120"), Decimal("0.1")),
        ("CLOSE", Decimal("1"), Decimal("110"), Decimal("0.1")),
    ]
    # PnL: (120-100)*1 + (110-100)*1 = 20 + 10 = 30, minus fees 0.3 = 29.7
    assert realized_pnl_fifo(fills) == Decimal("29.7")

def test_fifo_long_loss():
    """Test losing FIFO calculation"""
    fills = [
        ("OPEN",  Decimal("2"), Decimal("100"), Decimal("0.1")),
        ("CLOSE", Decimal("1"), Decimal("80"),  Decimal("0.1")),
        ("CLOSE", Decimal("1"), Decimal("90"),  Decimal("0.1")),
    ]
    # PnL: (80-100)*1 + (90-100)*1 = -20 + -10 = -30, minus fees 0.3 = -30.3
    assert realized_pnl_fifo(fills) == Decimal("-30.3")

def test_fifo_partial_close():
    """Test partial position closing"""
    fills = [
        ("OPEN",  Decimal("3"), Decimal("100"), Decimal("0.1")),
        ("CLOSE", Decimal("1.5"), Decimal("120"), Decimal("0.15")),
        ("CLOSE", Decimal("1.5"), Decimal("110"), Decimal("0.15")),
    ]
    # PnL: (120-100)*1.5 + (110-100)*1.5 = 30 + 15 = 45, minus fees 0.4 = 44.6
    assert realized_pnl_fifo(fills) == Decimal("44.6")

def test_fifo_no_closes():
    """Test with only opens (no realized PnL)"""
    fills = [
        ("OPEN", Decimal("1"), Decimal("100"), Decimal("0.1")),
        ("OPEN", Decimal("1"), Decimal("110"), Decimal("0.1")),
    ]
    # Only fees: -0.2
    assert realized_pnl_fifo(fills) == Decimal("-0.2")

def test_fifo_no_fills():
    """Test with no fills"""
    fills = []
    assert realized_pnl_fifo(fills) == Decimal("0")

def test_fifo_mixed_sizes():
    """Test with different position sizes"""
    fills = [
        ("OPEN",  Decimal("0.5"), Decimal("100"), Decimal("0.05")),
        ("OPEN",  Decimal("1.5"), Decimal("110"), Decimal("0.15")),
        ("CLOSE", Decimal("1"),   Decimal("120"), Decimal("0.1")),
        ("CLOSE", Decimal("1"),   Decimal("90"),  Decimal("0.1")),
    ]
    # PnL: (120-100)*0.5 + (120-110)*0.5 + (90-110)*1 = 10 + 5 - 20 = -5, minus fees 0.4 = -5.4
    assert realized_pnl_fifo(fills) == Decimal("-5.4")

if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])
