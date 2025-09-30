"""Unit tests for positions repository (Phase 4)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base
from src.repositories.positions_repo import (
    get_position,
    list_positions,
    upsert_position,
)


class TestPositionsRepo:
    """Test positions repository functions."""

    @pytest.fixture
    def db_session(self, tmp_path):
        """Create in-memory SQLite session."""
        eng = create_engine(f"sqlite:///{tmp_path}/test.db")
        Base.metadata.create_all(eng)
        Session = sessionmaker(bind=eng)
        session = Session()
        yield session
        session.close()

    def test_upsert_and_get(self, db_session) -> None:
        """Test position upsert and retrieval."""
        pos = upsert_position(db_session, "0xabc", "BTC-USD", True, 1_000_000, 500_000)

        assert pos.user_address == "0xabc"
        assert pos.symbol == "BTC-USD"
        assert pos.size_usd_1e6 == 1_000_000
        assert pos.entry_collateral_1e6 == 500_000

        # Retrieve
        retrieved = get_position(db_session, "0xabc", "BTC-USD")
        assert retrieved is not None
        assert retrieved.size_usd_1e6 == 1_000_000

    def test_upsert_updates_existing(self, db_session) -> None:
        """Test that upsert updates existing position."""
        # Create
        upsert_position(db_session, "0xabc", "ETH-USD", True, 1_000_000, 500_000)

        # Update
        pos = upsert_position(db_session, "0xabc", "ETH-USD", True, 500_000, 250_000)

        assert pos.size_usd_1e6 == 1_500_000  # 1M + 500k
        assert pos.entry_collateral_1e6 == 750_000  # 500k + 250k

    def test_list_positions_only_active(self, db_session) -> None:
        """Test that list_positions only returns active positions."""
        # Create positions
        upsert_position(db_session, "0xabc", "BTC-USD", True, 1_000_000, 500_000)
        upsert_position(db_session, "0xabc", "ETH-USD", True, 0, 0)  # Zero size

        positions = list_positions(db_session, "0xabc")

        # Only BTC-USD should be returned (ETH-USD has zero size)
        assert len(positions) == 1
        assert positions[0].symbol == "BTC-USD"

    def test_position_address_normalization(self, db_session) -> None:
        """Test that addresses are normalized to lowercase."""
        upsert_position(db_session, "0xABC", "BTC-USD", True, 1_000_000, 500_000)

        # Retrieve with different case
        pos = get_position(db_session, "0xabc", "BTC-USD")
        assert pos is not None
        assert pos.user_address == "0xabc"
