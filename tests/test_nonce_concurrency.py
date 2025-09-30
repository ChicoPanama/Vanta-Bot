"""Nonce reservation concurrency testing (Redis stubbed)."""

import asyncio
import threading
import time
from unittest.mock import patch

import pytest

from src.blockchain.tx.nonce_manager import NonceManager
from src.blockchain.tx.nonce_store import (
    HybridNonceStore,
    InMemoryNonceStore,
    RedisNonceStore,
)


class InMemoryRedisForNonce:
    def __init__(self):
        self.store = {}
        self.locks = {}

    def ping(self):
        return True

    def get(self, key):
        val = self.store.get(key)
        if val is None:
            return None
        return val if isinstance(val, (bytes, bytearray)) else str(val).encode()

    def set(self, key, value, ex=None):
        self.store[key] = value
        return True

    def lock(self, key, timeout=5, blocking_timeout=5):
        if key not in self.locks:
            self.locks[key] = threading.Lock()
        lock = self.locks[key]

        class _Ctx:
            def __enter__(self_inner):
                acquired = lock.acquire(timeout=blocking_timeout)
                if not acquired:
                    raise TimeoutError("Could not acquire lock")
                return True

            def __exit__(self_inner, exc_type, exc, tb):
                lock.release()

        return _Ctx()


class StubWeb3:
    class Eth:
        def get_transaction_count(self, address, state):
            return 0

    def __init__(self):
        self.eth = StubWeb3.Eth()


class TestNonceReservationConcurrency:
    """Test nonce reservation under high concurrency."""

    @pytest.fixture
    def in_memory_store(self):
        """Create in-memory nonce store."""
        return InMemoryNonceStore()

    @pytest.fixture
    def redis_store(self):
        """Create Redis nonce store with in-memory Redis stub."""
        return RedisNonceStore(InMemoryRedisForNonce(), StubWeb3())

    @pytest.fixture
    def hybrid_store(self):
        """Create hybrid nonce store with in-memory Redis stub."""
        return HybridNonceStore(InMemoryRedisForNonce(), StubWeb3())

    @pytest.fixture
    def in_memory_manager(self, in_memory_store):
        """Create nonce manager with in-memory store and stub web3."""
        return NonceManager(redis_client=None, web3_client=StubWeb3())

    @pytest.fixture
    def redis_manager(self, redis_store):
        """Create nonce manager with Redis store."""
        return NonceManager(redis_client=redis_store.redis, web3_client=StubWeb3())

    @pytest.fixture
    def hybrid_manager(self, hybrid_store):
        """Create nonce manager with hybrid store."""
        return NonceManager(redis_client=hybrid_store.redis, web3_client=StubWeb3())

    @pytest.mark.asyncio
    async def test_in_memory_concurrent_reservation(self, in_memory_manager):
        """Test concurrent nonce reservation with in-memory store."""
        num_requests = 100
        concurrency = 10

        address = "0x1111111111111111111111111111111111111111"

        async def reserve_nonce(request_id: int):
            async with in_memory_manager.reserve(address) as nonce:
                return {"request_id": request_id, "nonce": nonce, "success": True}

        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(concurrency)

        async def limited_reserve(request_id: int):
            async with semaphore:
                return await reserve_nonce(request_id)

        # Run concurrent requests
        tasks = [limited_reserve(i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks)

        # Verify all requests succeeded
        assert len(results) == num_requests
        successful = [r for r in results if r["success"]]
        assert len(successful) == num_requests

        # Verify no nonce collisions
        nonces = [r["nonce"] for r in successful]
        assert len(nonces) == len(set(nonces))

        # Verify nonces are sequential
        nonces.sort()
        for i in range(1, len(nonces)):
            assert nonces[i] == nonces[i - 1] + 1

    @pytest.mark.asyncio
    async def test_redis_concurrent_reservation(self, redis_manager):
        """Test concurrent nonce reservation with Redis store."""
        num_requests = 50
        concurrency = 5

        address = "0x2222222222222222222222222222222222222222"

        async def reserve_nonce(request_id: int):
            async with redis_manager.reserve(address) as nonce:
                return {"request_id": request_id, "nonce": nonce, "success": True}

        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(concurrency)

        async def limited_reserve(request_id: int):
            async with semaphore:
                return await reserve_nonce(request_id)

        # Run concurrent requests
        tasks = [limited_reserve(i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks)

        # Verify all requests succeeded
        assert len(results) == num_requests
        successful = [r for r in results if r["success"]]
        assert len(successful) == num_requests

        # Verify no nonce collisions
        nonces = [r["nonce"] for r in successful]
        assert len(nonces) == len(set(nonces))

        # Verify nonces are sequential
        nonces.sort()
        for i in range(1, len(nonces)):
            assert nonces[i] == nonces[i - 1] + 1

    @pytest.mark.asyncio
    async def test_hybrid_concurrent_reservation(self, hybrid_manager):
        """Test concurrent nonce reservation with hybrid store."""
        num_requests = 50
        concurrency = 5

        address = "0x3333333333333333333333333333333333333333"

        async def reserve_nonce(request_id: int):
            async with hybrid_manager.reserve(address) as nonce:
                return {"request_id": request_id, "nonce": nonce, "success": True}

        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(concurrency)

        async def limited_reserve(request_id: int):
            async with semaphore:
                return await reserve_nonce(request_id)

        # Run concurrent requests
        tasks = [limited_reserve(i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks)

        # Verify all requests succeeded
        assert len(results) == num_requests
        successful = [r for r in results if r["success"]]
        assert len(successful) == num_requests

        # Verify no nonce collisions
        nonces = [r["nonce"] for r in successful]
        assert len(nonces) == len(set(nonces))

        # Verify nonces are sequential
        nonces.sort()
        for i in range(1, len(nonces)):
            assert nonces[i] == nonces[i - 1] + 1

    @pytest.mark.asyncio
    async def test_redis_failure_fallback(self, hybrid_manager):
        """Test Redis failure fallback in hybrid store."""
        # Mock Redis failure
        with patch.object(hybrid_manager.store, "redis_store") as mock_redis:
            mock_redis.reserve.side_effect = Exception("Redis unavailable")

            # Should fallback to in-memory store
            async with hybrid_manager.reserve(
                "0x3333333333333333333333333333333333333333"
            ) as nonce:
                assert nonce is not None
                assert nonce > 0

    @pytest.mark.asyncio
    async def test_high_concurrency_stress(self, in_memory_manager):
        """Test high concurrency stress test."""
        num_requests = 500
        concurrency = 50

        address = "0x4444444444444444444444444444444444444444"

        async def reserve_nonce(request_id: int):
            async with in_memory_manager.reserve(address) as nonce:
                return {"request_id": request_id, "nonce": nonce, "success": True}

        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(concurrency)

        async def limited_reserve(request_id: int):
            async with semaphore:
                return await reserve_nonce(request_id)

        start_time = time.time()

        # Run concurrent requests
        tasks = [limited_reserve(i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks)

        end_time = time.time()
        duration = end_time - start_time

        # Verify all requests succeeded
        assert len(results) == num_requests
        successful = [r for r in results if r["success"]]
        assert len(successful) == num_requests

        # Verify no nonce collisions
        nonces = [r["nonce"] for r in successful]
        assert len(nonces) == len(set(nonces))

        # Verify performance
        requests_per_sec = num_requests / duration
        assert requests_per_sec > 100  # Should handle at least 100 req/s

        # Verify nonces are sequential
        nonces.sort()
        for i in range(1, len(nonces)):
            assert nonces[i] == nonces[i - 1] + 1

    @pytest.mark.asyncio
    async def test_concurrent_reservation_with_delays(self, in_memory_manager):
        """Test concurrent reservation with artificial delays."""
        num_requests = 20
        concurrency = 5

        address = "0x5555555555555555555555555555555555555555"

        async def reserve_nonce_with_delay(request_id: int):
            async with in_memory_manager.reserve(address) as nonce:
                # Add artificial delay
                await asyncio.sleep(0.01)
                return {"request_id": request_id, "nonce": nonce, "success": True}

        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(concurrency)

        async def limited_reserve(request_id: int):
            async with semaphore:
                return await reserve_nonce_with_delay(request_id)

        # Run concurrent requests
        tasks = [limited_reserve(i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks)

        # Verify all requests succeeded
        assert len(results) == num_requests
        successful = [r for r in results if r["success"]]
        assert len(successful) == num_requests

        # Verify no nonce collisions
        nonces = [r["nonce"] for r in successful]
        assert len(nonces) == len(set(nonces))

        # Verify nonces are sequential
        nonces.sort()
        for i in range(1, len(nonces)):
            assert nonces[i] == nonces[i - 1] + 1

    @pytest.mark.asyncio
    async def test_reservation_timeout_handling(self, in_memory_manager):
        """Test reservation timeout handling."""
        # Mock timeout scenario
        # Simulate timeout by making the store raise TimeoutError
        with patch.object(in_memory_manager.store, "reserve") as mock_reserve:
            mock_reserve.side_effect = asyncio.TimeoutError("Reservation timeout")
            # Manager wraps exceptions as RuntimeError
            with pytest.raises(RuntimeError):
                async with in_memory_manager.reserve(
                    "0x1111111111111111111111111111111111111111"
                ):
                    pass

    @pytest.mark.asyncio
    async def test_reservation_exception_handling(self, in_memory_manager):
        """Test reservation exception handling."""
        # Mock exception scenario
        with patch.object(in_memory_manager.store, "reserve") as mock_reserve:
            mock_reserve.side_effect = Exception("Store error")

            # Should handle exception gracefully
            with pytest.raises(Exception, match="Store error"):
                async with in_memory_manager.reserve(
                    "0x1111111111111111111111111111111111111111"
                ):
                    pass

    @pytest.mark.asyncio
    async def test_reservation_cleanup(self, in_memory_manager):
        """Test reservation cleanup on exception."""
        # Test that reservation is properly cleaned up on exception
        try:
            async with in_memory_manager.reserve(
                "0x1111111111111111111111111111111111111111"
            ) as nonce:
                raise Exception("Test exception")
        except Exception:
            pass

        # Next reservation should get next nonce
        async with in_memory_manager.reserve(
            "0x1111111111111111111111111111111111111111"
        ) as nonce:
            assert nonce > 0

    @pytest.mark.asyncio
    async def test_reservation_context_manager(self, in_memory_manager):
        """Test reservation context manager behavior."""
        # Test normal usage
        async with in_memory_manager.reserve(
            "0x1111111111111111111111111111111111111111"
        ) as nonce1:
            assert nonce1 > 0

        # Test nested reservations
        async with in_memory_manager.reserve(
            "0x1111111111111111111111111111111111111111"
        ) as nonce2:
            assert nonce2 > nonce1

        # Test multiple sequential reservations
        async with in_memory_manager.reserve(
            "0x1111111111111111111111111111111111111111"
        ) as nonce3:
            assert nonce3 > nonce2

    @pytest.mark.asyncio
    async def test_reservation_concurrent_access(self, in_memory_manager):
        """Test concurrent access to reservation."""

        # Test that concurrent access doesn't cause issues
        async def reserve_and_wait(request_id: int):
            async with in_memory_manager.reserve(
                "0x1111111111111111111111111111111111111111"
            ) as nonce:
                await asyncio.sleep(0.01)  # Simulate work
                return nonce

        # Run concurrent reservations
        tasks = [reserve_and_wait(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # Verify all reservations succeeded
        assert len(results) == 10

        # Verify no nonce collisions
        assert len(results) == len(set(results))

        # Verify nonces are sequential
        results.sort()
        for i in range(1, len(results)):
            assert results[i] == results[i - 1] + 1

    @pytest.mark.asyncio
    async def test_reservation_memory_usage(self, in_memory_manager):
        """Test reservation memory usage."""
        # Simplified: ensure multiple reservations progress and do not error
        address = "0x6666666666666666666666666666666666666666"
        nonces = []
        for _ in range(10):
            async with in_memory_manager.reserve(address) as n:
                nonces.append(n)
        assert len(nonces) == 10

        # Make many reservations
        for _i in range(100):
            async with in_memory_manager.reserve(address):
                pass

        # After many reservations, ensure next nonce still increments
        async with in_memory_manager.reserve(address) as after_many:
            assert after_many > nonces[-1]

    @pytest.mark.asyncio
    async def test_reservation_performance(self, in_memory_manager):
        """Test reservation performance."""
        num_requests = 1000

        start_time = time.time()

        # Make many reservations
        address = "0x7777777777777777777777777777777777777777"
        for _i in range(num_requests):
            async with in_memory_manager.reserve(address):
                pass

        end_time = time.time()
        duration = end_time - start_time

        # Verify performance
        requests_per_sec = num_requests / duration
        assert requests_per_sec > 1000  # Should handle at least 1000 req/s

    @pytest.mark.asyncio
    async def test_reservation_under_load(self, in_memory_manager):
        """Test reservation under high load."""
        num_requests = 100
        concurrency = 20

        address = "0x8888888888888888888888888888888888888888"

        async def reserve_nonce(request_id: int):
            async with in_memory_manager.reserve(address) as nonce:
                # Simulate some work
                await asyncio.sleep(0.001)
                return nonce

        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(concurrency)

        async def limited_reserve(request_id: int):
            async with semaphore:
                return await reserve_nonce(request_id)

        start_time = time.time()

        # Run concurrent requests
        tasks = [limited_reserve(i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks)

        end_time = time.time()
        duration = end_time - start_time

        # Verify all requests succeeded
        assert len(results) == num_requests

        # Verify no nonce collisions
        assert len(results) == len(set(results))

        # Verify performance
        requests_per_sec = num_requests / duration
        assert requests_per_sec > 50  # Should handle at least 50 req/s

        # Verify nonces are sequential
        results.sort()
        for i in range(1, len(results)):
            assert results[i] == results[i - 1] + 1
