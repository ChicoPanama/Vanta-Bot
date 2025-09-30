"""
Unit tests for copy store functionality
"""

import os
import sqlite3

# Import the copy store module
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.copytrading.copy_store import (
    DEFAULT_CFG,
    all_trader_keys,
    get,
    init,
    list_follows,
    put,
    remove,
    users_by_trader,
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_path = f.name

    # Set environment variable for the temp DB
    os.environ["USER_PREFS_DB"] = temp_path

    # Initialize the database
    init()

    yield temp_path

    # Cleanup
    os.unlink(temp_path)
    if "USER_PREFS_DB" in os.environ:
        del os.environ["USER_PREFS_DB"]


def test_init(temp_db):
    """Test database initialization"""
    # Check that tables exist
    con = sqlite3.connect(temp_db)
    try:
        cur = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='user_follow_configs'"
        )
        assert cur.fetchone() is not None, "user_follow_configs table should exist"

        # Check that index exists
        cur = con.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_follow_trader'"
        )
        assert cur.fetchone() is not None, "idx_follow_trader index should exist"
    finally:
        con.close()


def test_get_defaults(temp_db):
    """Test getting default configuration"""
    user_id = 12345
    trader_key = "test_trader"

    cfg = get(user_id, trader_key)

    # Should return defaults
    assert cfg == DEFAULT_CFG
    assert cfg["auto_copy"] is False
    assert cfg["notify"] is True
    assert cfg["sizing_mode"] == "MIRROR"


def test_put_and_get(temp_db):
    """Test storing and retrieving configuration"""
    user_id = 12345
    trader_key = "test_trader"

    # Store custom config
    custom_config = {
        "auto_copy": True,
        "notify": False,
        "sizing_mode": "FIXED_USD",
        "fixed_usd": 250.0,
        "max_leverage": 25,
    }

    put(user_id, trader_key, custom_config)

    # Retrieve and verify
    retrieved = get(user_id, trader_key)
    assert retrieved["auto_copy"] is True
    assert retrieved["notify"] is False
    assert retrieved["sizing_mode"] == "FIXED_USD"
    assert retrieved["fixed_usd"] == 250.0
    assert retrieved["max_leverage"] == 25

    # Should merge with defaults
    assert retrieved["per_trade_cap_usd"] == DEFAULT_CFG["per_trade_cap_usd"]


def test_remove(temp_db):
    """Test removing configuration"""
    user_id = 12345
    trader_key = "test_trader"

    # Store config
    put(user_id, trader_key, {"auto_copy": True})

    # Verify it exists
    cfg = get(user_id, trader_key)
    assert cfg["auto_copy"] is True

    # Remove it
    remove(user_id, trader_key)

    # Should return defaults
    cfg = get(user_id, trader_key)
    assert cfg == DEFAULT_CFG


def test_list_follows(temp_db):
    """Test listing user's follows"""
    user_id = 12345

    # Add multiple follows
    put(user_id, "trader1", {"auto_copy": True})
    put(user_id, "trader2", {"auto_copy": False})
    put(user_id, "trader3", {"notify": True})

    # List follows
    follows = list_follows(user_id)
    assert len(follows) == 3

    # Check order (should be alphabetical)
    trader_keys = [tk for tk, _ in follows]
    assert trader_keys == ["trader1", "trader2", "trader3"]

    # Check configurations
    configs = [cfg for _, cfg in follows]
    assert configs[0]["auto_copy"] is True
    assert configs[1]["auto_copy"] is False
    assert configs[2]["notify"] is True


def test_users_by_trader(temp_db):
    """Test reverse lookup - users following a trader"""
    trader_key = "popular_trader"

    # Multiple users follow the same trader
    put(111, trader_key, {"auto_copy": True})
    put(222, trader_key, {"auto_copy": False})
    put(333, trader_key, {"notify": True})

    # Another user follows different trader
    put(444, "other_trader", {"auto_copy": True})

    # Get users following popular_trader
    users = users_by_trader(trader_key)
    assert len(users) == 3
    assert set(users) == {111, 222, 333}

    # Get users following other_trader
    users = users_by_trader("other_trader")
    assert len(users) == 1
    assert users[0] == 444


def test_all_trader_keys(temp_db):
    """Test getting all unique trader keys"""
    # Add follows for multiple traders
    put(111, "trader_a", {"auto_copy": True})
    put(222, "trader_b", {"auto_copy": False})
    put(333, "trader_a", {"notify": True})  # Same trader, different user
    put(444, "trader_c", {"auto_copy": True})

    # Get all trader keys
    keys = all_trader_keys()
    assert len(keys) == 3
    assert set(keys) == {"trader_a", "trader_b", "trader_c"}

    # Should be sorted
    assert keys == ["trader_a", "trader_b", "trader_c"]


def test_wal_mode(temp_db):
    """Test WAL mode is enabled"""
    con = sqlite3.connect(temp_db)
    try:
        cur = con.execute("PRAGMA journal_mode")
        journal_mode = cur.fetchone()[0]
        assert journal_mode.upper() == "WAL", f"Expected WAL mode, got {journal_mode}"
    finally:
        con.close()


def test_index_performance(temp_db):
    """Test that index improves query performance"""
    trader_key = "test_trader"

    # Add many follows to test index performance
    for i in range(100):
        put(i, trader_key, {"auto_copy": True})

    # Add some other traders
    for i in range(50):
        put(i, f"other_trader_{i}", {"auto_copy": True})

    # Query should be fast due to index
    users = users_by_trader(trader_key)
    assert len(users) == 100

    # Test index exists
    con = sqlite3.connect(temp_db)
    try:
        cur = con.execute(
            "EXPLAIN QUERY PLAN SELECT user_id FROM user_follow_configs WHERE trader_key=?",
            (trader_key,),
        )
        plan = cur.fetchone()[3]
        assert "idx_follow_trader" in plan, "Query should use the index"
    finally:
        con.close()


def test_concurrent_access(temp_db):
    """Test basic concurrent access safety"""
    import threading

    results = []
    errors = []

    def worker(user_id_offset):
        try:
            for i in range(10):
                user_id = user_id_offset * 100 + i
                trader_key = f"trader_{i % 5}"

                # Store config
                put(user_id, trader_key, {"auto_copy": True})

                # Retrieve config
                cfg = get(user_id, trader_key)
                assert cfg["auto_copy"] is True

                results.append((user_id, trader_key))

        except Exception as e:
            errors.append(e)

    # Run multiple threads
    threads = []
    for i in range(5):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()

    # Wait for completion
    for t in threads:
        t.join()

    # Check results
    assert len(errors) == 0, f"Errors during concurrent access: {errors}"
    assert len(results) == 50, f"Expected 50 operations, got {len(results)}"

    # Verify data integrity
    for user_id, trader_key in results:
        cfg = get(user_id, trader_key)
        assert cfg["auto_copy"] is True
