"""Tests for TP/SL repository (Phase 7)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base
from src.repositories.tpsl_repo import add_tpsl, deactivate_tpsl, list_tpsl


class TestTPSLRepo:
    @pytest.fixture
    def db_session(self, tmp_path):
        eng = create_engine(f"sqlite:///{tmp_path}/test.db")
        Base.metadata.create_all(eng)
        Session = sessionmaker(bind=eng)
        session = Session()
        yield session
        session.close()

    def test_add_tpsl(self, db_session) -> None:
        rec = add_tpsl(db_session, 123, "BTC-USD", True, tp=55000.0, sl=45000.0)
        assert rec.tg_user_id == 123
        assert rec.symbol == "BTC-USD"
        assert rec.take_profit_price == 55000.0
        assert rec.stop_loss_price == 45000.0
        assert rec.active is True

    def test_list_tpsl_only_active(self, db_session) -> None:
        add_tpsl(db_session, 123, "BTC-USD", True, 55000, 45000)
        rec2 = add_tpsl(db_session, 123, "ETH-USD", True, 3000, 2500)
        deactivate_tpsl(db_session, rec2.id)

        active = list_tpsl(db_session, 123)
        assert len(active) == 1
        assert active[0].symbol == "BTC-USD"
