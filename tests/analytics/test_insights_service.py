"""Tests for the analytics InsightsService."""

from datetime import datetime, timezone

import pytest

try:  # pragma: no cover - optional dependency for local runs
    import sqlalchemy  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover
    pytest.skip("SQLAlchemy not installed", allow_module_level=True)

import src.database.operations as db_module
import src.services.analytics.insights_service as insights_module
from src.database.operations import DatabaseManager
from src.services.analytics.insights_service import InsightsService


@pytest.fixture()
async def temp_db(tmp_path):
    db_path = tmp_path / "insights.db"
    manager = DatabaseManager(database_url=f"sqlite+aiosqlite:///{db_path}")
    await manager.create_tables()

    original_db = db_module.db
    original_service_db = insights_module.db
    db_module.db = manager
    insights_module.db = manager

    try:
        yield manager
    finally:
        db_module.db = original_db
        insights_module.db = original_service_db
        await manager.engine.dispose()


@pytest.mark.asyncio
async def test_leaderboard_and_market_signal(temp_db):
    service = InsightsService()

    user = await temp_db.create_user(
        telegram_id=12345,
        username="leader",
        wallet_address="0xabc",
        encrypted_private_key="key",
    )

    await temp_db.create_position(
        user_id=user.id,
        symbol="ETH-USD",
        side="LONG",
        size=2.0,
        leverage=5,
        entry_price=1800.0,
    )

    closed_pos = await temp_db.create_position(
        user_id=user.id,
        symbol="ETH-USD",
        side="LONG",
        size=1.0,
        leverage=3,
        entry_price=1700.0,
    )
    await temp_db.update_position(
        closed_pos.id,
        status="CLOSED",
        pnl=350.0,
        closed_at=datetime.now(timezone.utc),
    )

    leaderboard = await service.get_leaderboard()
    assert leaderboard
    assert leaderboard[0]["total_pnl"] >= 350.0

    signal = await service.get_market_signal()
    assert signal["signal"] in {"green", "yellow", "red"}
    assert "confidence" in signal

    dashboard = await service.get_dashboard()
    assert dashboard["signals"]
