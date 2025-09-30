"""Unit tests for sync state repository (Phase 4)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base
from src.repositories.sync_state_repo import get_block, set_block


class TestSyncStateRepo:
    """Test sync state repository functions."""

    @pytest.fixture
    def db_session(self, tmp_path):
        """Create in-memory SQLite session."""
        eng = create_engine(f"sqlite:///{tmp_path}/test.db")
        Base.metadata.create_all(eng)
        Session = sessionmaker(bind=eng)
        session = Session()
        yield session
        session.close()

    def test_get_block_returns_zero_for_new(self, db_session) -> None:
        """Test get_block returns 0 for non-existent indexer."""
        block = get_block(db_session, "new_indexer")
        assert block == 0

    def test_set_and_get_block(self, db_session) -> None:
        """Test setting and retrieving block number."""
        set_block(db_session, "test_indexer", 12345)
        block = get_block(db_session, "test_indexer")
        assert block == 12345

    def test_set_block_updates_existing(self, db_session) -> None:
        """Test that set_block updates existing state."""
        set_block(db_session, "test_indexer", 100)
        set_block(db_session, "test_indexer", 200)

        block = get_block(db_session, "test_indexer")
        assert block == 200
