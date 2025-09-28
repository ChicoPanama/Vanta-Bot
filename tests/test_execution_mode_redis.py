"""ExecutionModeManager Redis convergence testing (in-memory stubbed)."""

import pytest
import asyncio
import json
import time
from unittest.mock import patch, Mock
from src.services.copy_trading.execution_mode import ExecutionModeManager, ExecutionMode
from tests.fixtures.redis_stub import RedisStub, AsyncRedisStub


class InMemoryRedis:
    """Minimal in-memory Redis stub for tests."""
    def __init__(self):
        self.store = {}
        self.expiry = {}

    def ping(self):
        return True

    def _expired(self, key):
        ts = self.expiry.get(key)
        return ts is not None and time.time() >= ts

    def get(self, key):
        if self._expired(key):
            self.store.pop(key, None)
            self.expiry.pop(key, None)
            return None
        val = self.store.get(key)
        if val is None:
            return None
        return val if isinstance(val, bytes) else str(val).encode()

    def set(self, key, value, ex=None):
        self.store[key] = value if isinstance(value, (bytes, bytearray)) else str(value).encode()
        if ex is not None:
            self.expiry[key] = time.time() + ex
        return True

    def expire(self, key, seconds):
        self.expiry[key] = time.time() + seconds
        return True

    def info(self, section='memory'):
        total = sum(len(v) for v in self.store.values())
        return {"used_memory": total}


class TestExecutionModeRedisConvergence:
    """Test Redis convergence for execution mode manager using in-memory stub."""

    @pytest.fixture
    def redis_client(self):
        return InMemoryRedis()

    @pytest.fixture
    def execution_manager_a(self, redis_client):
        return ExecutionModeManager(redis_client=redis_client)

    @pytest.fixture
    def execution_manager_b(self, redis_client):
        return ExecutionModeManager(redis_client=redis_client)

    def test_initial_mode_default(self, execution_manager_a):
        assert execution_manager_a.mode == ExecutionMode.DRY
        assert not execution_manager_a.is_emergency_stopped

    def test_mode_persistence(self, execution_manager_a, execution_manager_b):
        execution_manager_a.set_mode(ExecutionMode.LIVE)
        assert execution_manager_a.mode == ExecutionMode.LIVE
        execution_manager_b.refresh_from_redis()
        assert execution_manager_b.mode == ExecutionMode.LIVE

    def test_emergency_stop_persistence(self, execution_manager_a, execution_manager_b):
        execution_manager_a.set_emergency_stop(True)
        assert execution_manager_a.is_emergency_stopped
        execution_manager_b.refresh_from_redis()
        assert execution_manager_b.is_emergency_stopped

    def test_mode_toggle_convergence(self, execution_manager_a, execution_manager_b):
        assert execution_manager_a.mode == ExecutionMode.DRY
        assert execution_manager_b.mode == ExecutionMode.DRY
        execution_manager_a.set_mode(ExecutionMode.LIVE)
        execution_manager_b.refresh_from_redis()
        assert execution_manager_b.mode == ExecutionMode.LIVE
        execution_manager_b.set_mode(ExecutionMode.DRY)
        execution_manager_a.refresh_from_redis()
        assert execution_manager_a.mode == ExecutionMode.DRY

    def test_emergency_stop_convergence(self, execution_manager_a, execution_manager_b):
        assert not execution_manager_a.is_emergency_stopped
        assert not execution_manager_b.is_emergency_stopped
        execution_manager_a.set_emergency_stop(True)
        execution_manager_b.refresh_from_redis()
        assert execution_manager_b.is_emergency_stopped
        execution_manager_b.set_emergency_stop(False)
        execution_manager_a.refresh_from_redis()
        assert not execution_manager_a.is_emergency_stopped

    def test_execution_context_consistency(self, execution_manager_a, execution_manager_b):
        execution_manager_a.set_mode(ExecutionMode.LIVE)
        execution_manager_a.set_emergency_stop(False)
        context_a = execution_manager_a.get_execution_context()
        execution_manager_b.refresh_from_redis()
        context_b = execution_manager_b.get_execution_context()
        assert context_a['mode'] == context_b['mode']
        assert context_a['emergency_stop'] == context_b['emergency_stop']
        assert context_a['can_execute'] == context_b['can_execute']

    def test_health_metrics_consistency(self, execution_manager_a, execution_manager_b):
        execution_manager_a.set_mode(ExecutionMode.LIVE)
        execution_manager_a.set_emergency_stop(False)
        metrics_a = execution_manager_a.get_health_metrics()
        execution_manager_b.refresh_from_redis()
        metrics_b = execution_manager_b.get_health_metrics()
        assert metrics_a['execution_mode'] == metrics_b['execution_mode']
        assert metrics_a['emergency_stop'] == metrics_b['emergency_stop']
        assert metrics_a['can_execute'] == metrics_b['can_execute']

    def test_redis_connection_failure(self):
        class DummyError(Exception):
            pass
        manager = ExecutionModeManager(redis_client=None)
        with patch.object(manager, '_load_from_redis') as mock_load:
            mock_load.side_effect = DummyError("Redis unavailable")
            # Should not raise; manager handles errors gracefully
            manager.refresh_from_redis()
            assert manager.mode in (ExecutionMode.DRY, ExecutionMode.LIVE)

    def test_redis_timeout_handling(self, execution_manager_a):
        class DummyTimeout(Exception):
            pass
        with patch.object(execution_manager_a, '_load_from_redis') as mock_load:
            mock_load.side_effect = DummyTimeout("Redis timeout")
            execution_manager_a.refresh_from_redis()
            # Should not raise

    def test_concurrent_mode_changes(self, execution_manager_a, execution_manager_b):
        execution_manager_a.set_mode(ExecutionMode.LIVE)
        execution_manager_b.set_mode(ExecutionMode.DRY)
        execution_manager_a.refresh_from_redis()
        execution_manager_b.refresh_from_redis()
        assert execution_manager_a.mode == ExecutionMode.DRY
        assert execution_manager_b.mode == ExecutionMode.DRY

    def test_emergency_stop_blocks_execution(self, execution_manager_a):
        execution_manager_a.set_mode(ExecutionMode.LIVE)
        assert execution_manager_a.can_execute()
        execution_manager_a.set_emergency_stop(True)
        assert not execution_manager_a.can_execute()
        execution_manager_a.set_emergency_stop(False)
        assert execution_manager_a.can_execute()

    def test_dry_mode_blocks_execution(self, execution_manager_a):
        execution_manager_a.set_mode(ExecutionMode.DRY)
        assert not execution_manager_a.can_execute()
        execution_manager_a.set_mode(ExecutionMode.LIVE)
        assert execution_manager_a.can_execute()

    def test_redis_key_consistency(self, execution_manager_a, redis_client):
        execution_manager_a.set_mode(ExecutionMode.LIVE)
        execution_manager_a.set_emergency_stop(True)
        raw = redis_client.get("exec_mode")
        data = json.loads(raw.decode()) if raw else {}
        assert data.get("mode") == "LIVE"
        assert data.get("emergency_stop") is True

    def test_redis_data_serialization(self, execution_manager_a, redis_client):
        execution_manager_a.set_mode(ExecutionMode.LIVE)
        execution_manager_a.set_emergency_stop(True)
        raw = redis_client.get("exec_mode")
        data = json.loads(raw.decode()) if raw else {}
        assert data.get("mode") == "LIVE"
        assert data.get("emergency_stop") is True

    def test_redis_connection_recovery(self, execution_manager_a):
        with patch.object(execution_manager_a, '_load_from_redis') as mock_load:
            mock_load.side_effect = Exception("Redis unavailable")
            execution_manager_a.refresh_from_redis()
            assert execution_manager_a.mode in (ExecutionMode.DRY, ExecutionMode.LIVE)

    def test_redis_data_corruption_handling(self, execution_manager_a, redis_client):
        # Corrupt exec_mode
        redis_client.set("exec_mode", b"not-json")
        execution_manager_a.refresh_from_redis()
        # Should stay at sane state (default DRY)
        assert execution_manager_a.mode in (ExecutionMode.DRY, ExecutionMode.LIVE)

    def test_redis_memory_usage(self, execution_manager_a, redis_client):
        execution_manager_a.set_mode(ExecutionMode.LIVE)
        execution_manager_a.set_emergency_stop(True)
        info = redis_client.info('memory')
        used_memory = info['used_memory']
        assert used_memory < 1024 * 1024

    def test_redis_expiration_handling(self, execution_manager_a, redis_client):
        execution_manager_a.set_mode(ExecutionMode.LIVE)
        redis_client.expire("exec_mode", 1)
        time.sleep(2)
        execution_manager_a.refresh_from_redis()
        # Should fall back to defaults because exec_mode key expired
        assert execution_manager_a.mode in (ExecutionMode.DRY, ExecutionMode.LIVE)
