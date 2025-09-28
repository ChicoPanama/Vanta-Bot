"""Tests for async DatabaseManager helpers."""

import sys
from pathlib import Path

import types

import pytest

try:  # pragma: no cover - optional dependency for local execution
    import sqlalchemy  # noqa: F401
except ModuleNotFoundError as exc:  # pragma: no cover
    sqlalchemy = None  # type: ignore
    pytest.skip("SQLAlchemy not installed", allow_module_level=True)  # type: ignore[misc]

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class _DummyLogger:
    def __getattr__(self, _name):  # pragma: no cover - testing stub
        def _noop(*_args, **_kwargs):
            return None

        return _noop


dummy_loguru = types.ModuleType("loguru")
dummy_loguru.logger = _DummyLogger()
sys.modules.setdefault("loguru", dummy_loguru)

try:
    from src.database.operations import DatabaseManager
except ModuleNotFoundError as exc:  # pragma: no cover
    pytest.skip(f"DatabaseManager import failed: {exc}", allow_module_level=True)


@pytest.fixture()
async def db_manager(tmp_path):
    db_path = tmp_path / "test_async.db"
    manager = DatabaseManager(database_url=f"sqlite+aiosqlite:///{db_path}")
    await manager.create_tables()
    yield manager
    await manager.engine.dispose()


@pytest.mark.asyncio
async def test_create_and_fetch_user(db_manager):
    created = await db_manager.create_user(
        telegram_id=42,
        username="async_tester",
        wallet_address="0x1234567890123456789012345678901234567890",
        encrypted_private_key="encrypted",
    )

    fetched = await db_manager.get_user(created.telegram_id)
    assert fetched is not None
    assert fetched.id == created.id


@pytest.mark.asyncio
async def test_position_lifecycle(db_manager):
    user = await db_manager.create_user(
        telegram_id=99,
        username="position_tester",
        wallet_address="0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
        encrypted_private_key="secret",
    )

    position = await db_manager.create_position(
        user_id=user.id,
        symbol="BTC",
        side="LONG",
        size=1.5,
        leverage=5,
        entry_price=25_000.0,
    )

    open_positions = await db_manager.get_user_positions(user.id, status="OPEN")
    assert len(open_positions) == 1
    assert open_positions[0].id == position.id

    updated = await db_manager.update_position(position.id, status="CLOSED", pnl=1250.0)
    assert updated is not None
    assert updated.status == "CLOSED"

    recent = await db_manager.list_recent_closed_positions(user.id, limit=5)
    assert recent
    assert recent[0].status == "CLOSED"


@pytest.mark.asyncio
async def test_pending_orders(db_manager):
    user = await db_manager.create_user(
        telegram_id=7,
        username="order_tester",
        wallet_address="0xfeedfeedfeedfeedfeedfeedfeedfeedfeedfeed",
        encrypted_private_key="order-secret",
    )

    await db_manager.create_order(
        user_id=user.id,
        symbol="ETH",
        order_type="LIMIT",
        side="LONG",
        size=2.0,
        leverage=3,
        price=1800.0,
    )

    pending = await db_manager.list_pending_orders(user.id)
    assert len(pending) == 1
    assert pending[0].symbol == "ETH"
