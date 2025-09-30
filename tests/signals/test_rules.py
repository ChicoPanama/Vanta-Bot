"""Tests for signal rules (Phase 6)."""

from src.signals.rules import Decision, evaluate_close, evaluate_open


class DummyDB:
    """Dummy database for testing."""

    pass


class TestSignalRules:
    """Test signal rule evaluation."""

    def test_evaluate_open_pass(self) -> None:
        """Test that valid open signal passes."""
        decision = evaluate_open(DummyDB(), 1, "BTC-USD", "LONG", 10.0, 2)
        assert decision.allow is True

    def test_evaluate_open_invalid_side(self) -> None:
        """Test that invalid side is rejected."""
        decision = evaluate_open(DummyDB(), 1, "BTC-USD", "INVALID", 10.0, 2)
        assert decision.allow is False
        assert "not allowed" in decision.reason.lower()

    def test_evaluate_open_invalid_symbol(self) -> None:
        """Test that invalid symbol is rejected."""
        decision = evaluate_open(DummyDB(), 1, "INVALID-USD", "LONG", 10.0, 2)
        assert decision.allow is False
        assert "not allowed" in decision.reason.lower()

    def test_evaluate_open_excessive_leverage(self) -> None:
        """Test that excessive leverage is rejected."""
        decision = evaluate_open(DummyDB(), 1, "BTC-USD", "LONG", 10.0, 100)
        assert decision.allow is False
        assert "Leverage" in decision.reason

    def test_evaluate_close_pass(self) -> None:
        """Test that valid close signal passes."""
        decision = evaluate_close(DummyDB(), 1, "BTC-USD", 5.0)
        assert decision.allow is True

    def test_evaluate_close_invalid_symbol(self) -> None:
        """Test that invalid symbol is rejected."""
        decision = evaluate_close(DummyDB(), 1, "INVALID-USD", 5.0)
        assert decision.allow is False

    def test_evaluate_close_zero_reduce(self) -> None:
        """Test that zero reduce is rejected."""
        decision = evaluate_close(DummyDB(), 1, "BTC-USD", 0.0)
        assert decision.allow is False
