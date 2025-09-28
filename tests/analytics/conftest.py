import os
import pytest

@pytest.fixture(autouse=True)
def seed_trader_tables(monkeypatch):
    # No real DB here; analytics services in tests tend to AsyncMock their DB layer
    # This fixture exists as a placeholder hook should future tests rely on actual inserts.
    os.environ.setdefault('LEADER_ACTIVE_HOURS', '72')
    os.environ.setdefault('LEADER_MIN_TRADES_30D', '10')
    os.environ.setdefault('LEADER_MIN_VOLUME_30D_USD', '10000')
    yield
