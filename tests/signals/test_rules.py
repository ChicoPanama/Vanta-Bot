"""Tests for signal rules (Phase 6)."""

from unittest.mock import Mock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.database.models import Base, UserRiskPolicy
from src.signals.rules import Decision, evaluate_close, evaluate_open


class TestSignalRules:
    """Test signal rule evaluation."""

    @pytest.fixture
    def db_session(self):
        """Create in-memory SQLite session with default risk policy."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        session = Session(engine)

        # Create default risk policy for test user
        policy = UserRiskPolicy(
            tg_user_id=1,
            max_leverage_x=50,
            max_position_usd_1e6=10_000_000_000,
            circuit_breaker=False,
        )
        session.add(policy)
        session.commit()

        yield session
        session.close()

    def test_evaluate_open_pass(self, db_session) -> None:
        """Test that valid open signal passes."""
        decision = evaluate_open(db_session, 1, "BTC-USD", "LONG", 10.0, 2)
        assert decision.allow is True

    def test_evaluate_open_invalid_side(self, db_session) -> None:
        """Test that invalid side is rejected."""
        decision = evaluate_open(db_session, 1, "BTC-USD", "INVALID", 10.0, 2)
        assert decision.allow is False
        assert "not allowed" in decision.reason.lower()

    def test_evaluate_open_invalid_symbol(self, db_session) -> None:
        """Test that invalid symbol is rejected."""
        decision = evaluate_open(db_session, 1, "INVALID-USD", "LONG", 10.0, 2)
        assert decision.allow is False
        assert "not allowed" in decision.reason.lower()

    def test_evaluate_open_excessive_leverage(self, db_session) -> None:
        """Test that excessive leverage is rejected."""
        # User policy has max_leverage_x=50, so 100 should be rejected
        decision = evaluate_open(db_session, 1, "BTC-USD", "LONG", 10.0, 100)
        assert decision.allow is False
        assert "Leverage" in decision.reason

    def test_evaluate_close_pass(self, db_session) -> None:
        """Test that valid close signal passes."""
        decision = evaluate_close(db_session, 1, "BTC-USD", 5.0)
        assert decision.allow is True

    def test_evaluate_close_invalid_symbol(self, db_session) -> None:
        """Test that invalid symbol is rejected."""
        decision = evaluate_close(db_session, 1, "INVALID-USD", 5.0)
        assert decision.allow is False

    def test_evaluate_close_zero_reduce(self, db_session) -> None:
        """Test that zero reduce is rejected."""
        decision = evaluate_close(db_session, 1, "BTC-USD", 0.0)
        assert decision.allow is False
