"""Tests for rules with per-user policies (Phase 7)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base
from src.repositories.risk_repo import update_policy
from src.signals.rules import evaluate_open


class TestRulesWithPolicy:
    @pytest.fixture
    def db_session(self, tmp_path):
        eng = create_engine(f"sqlite:///{tmp_path}/test.db")
        Base.metadata.create_all(eng)
        Session = sessionmaker(bind=eng)
        session = Session()
        yield session
        session.close()

    def test_circuit_breaker_blocks(self, db_session) -> None:
        update_policy(db_session, 123, circuit_breaker=True)
        decision = evaluate_open(db_session, 123, "BTC-USD", "LONG", 10.0, 2)
        assert decision.allow is False
        assert "Circuit breaker" in decision.reason

    def test_user_leverage_limit(self, db_session) -> None:
        update_policy(db_session, 123, max_leverage_x=5)
        decision = evaluate_open(db_session, 123, "BTC-USD", "LONG", 10.0, 10)
        assert decision.allow is False
        assert "Leverage>5x" in decision.reason

    def test_user_position_limit(self, db_session) -> None:
        update_policy(db_session, 123, max_position_usd_1e6=1_000_000)  # $1
        decision = evaluate_open(
            db_session, 123, "BTC-USD", "LONG", 10.0, 2
        )  # $20 position
        assert decision.allow is False
        assert "Exceeds max position" in decision.reason
