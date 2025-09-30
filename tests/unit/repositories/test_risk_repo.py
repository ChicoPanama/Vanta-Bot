"""Tests for risk repository (Phase 7)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base
from src.repositories.risk_repo import get_or_create_policy, update_policy


class TestRiskRepo:
    @pytest.fixture
    def db_session(self, tmp_path):
        eng = create_engine(f"sqlite:///{tmp_path}/test.db")
        Base.metadata.create_all(eng)
        Session = sessionmaker(bind=eng)
        session = Session()
        yield session
        session.close()

    def test_get_or_create_creates_with_defaults(self, db_session) -> None:
        pol = get_or_create_policy(db_session, 123)
        assert pol.tg_user_id == 123
        assert pol.max_leverage_x == 20
        assert pol.max_position_usd_1e6 == 100_000_000

    def test_get_or_create_retrieves_existing(self, db_session) -> None:
        pol1 = get_or_create_policy(db_session, 123)
        pol2 = get_or_create_policy(db_session, 123)
        assert pol1.id == pol2.id

    def test_update_policy(self, db_session) -> None:
        pol = update_policy(db_session, 123, max_leverage_x=10, circuit_breaker=True)
        assert pol.max_leverage_x == 10
        assert pol.circuit_breaker is True
