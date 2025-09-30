"""Tests for user wallets repository (Phase 5)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base
from src.repositories.user_wallets_repo import bind_wallet, get_wallet


class TestUserWalletsRepo:
    """Test user wallet binding repository."""

    @pytest.fixture
    def db_session(self, tmp_path):
        """Create in-memory SQLite session."""
        eng = create_engine(f"sqlite:///{tmp_path}/test.db")
        Base.metadata.create_all(eng)
        Session = sessionmaker(bind=eng)
        session = Session()
        yield session
        session.close()

    def test_bind_and_get(self, db_session) -> None:
        """Test wallet binding and retrieval."""
        addr = "0x0000000000000000000000000000000000000001"
        rec = bind_wallet(db_session, 123, addr)

        assert rec.tg_user_id == 123
        assert rec.address.lower() == addr.lower()

        # Retrieve
        retrieved = get_wallet(db_session, 123)
        assert retrieved is not None
        assert retrieved.lower() == addr.lower()

    def test_get_wallet_returns_none_for_unbound(self, db_session) -> None:
        """Test get_wallet returns None for unbound user."""
        addr = get_wallet(db_session, 999)
        assert addr is None

    def test_bind_updates_existing(self, db_session) -> None:
        """Test that binding updates existing record."""
        addr1 = "0x0000000000000000000000000000000000000001"
        addr2 = "0x0000000000000000000000000000000000000002"

        bind_wallet(db_session, 123, addr1)
        rec = bind_wallet(db_session, 123, addr2)

        assert rec.address.lower() == addr2.lower()

        # Verify only one record exists
        retrieved = get_wallet(db_session, 123)
        assert retrieved.lower() == addr2.lower()
