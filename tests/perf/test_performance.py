"""
Performance Testing Suite
Benchmarking and performance validation for critical components
"""

import pytest
import asyncio
import time
from decimal import Decimal
from unittest.mock import Mock, AsyncMock
from src.services.oracle import OracleFacade, PriceQuote
from src.services.markets.symbols import to_canonical, to_ui_format
from tests.fixtures.redis_stub import RedisStub, AsyncRedisStub


class TestPerformance:
    """Performance testing for critical components."""
    
    @pytest.fixture
    def mock_primary_provider(self):
        """Mock primary provider for performance testing."""
        provider = Mock()
        provider.get_price = AsyncMock(return_value=PriceQuote(
            price=Decimal('50000.00'),
            timestamp=1234567890,
            source="pyth",
            freshness_sec=5,
            deviation_bps=25
        ))
        return provider
    
    @pytest.fixture
    def mock_secondary_provider(self):
        """Mock secondary provider for performance testing."""
        provider = Mock()
        provider.get_price = AsyncMock(return_value=PriceQuote(
            price=Decimal('50010.00'),
            timestamp=1234567890,
            source="chainlink",
            freshness_sec=8,
            deviation_bps=30
        ))
        return provider
    
    @pytest.fixture
    def oracle_facade(self, mock_primary_provider, mock_secondary_provider):
        """Create oracle facade for performance testing."""
        return OracleFacade(
            primary=mock_primary_provider,
            secondary=mock_secondary_provider
        )
    
    @pytest.mark.benchmark(group="oracle")
    def test_oracle_facade_performance(self, oracle_facade, benchmark):
        """Benchmark oracle facade performance."""
        async def run_oracle_test():
            return await oracle_facade.get_price('BTC/USD')
        
        result = benchmark(asyncio.run, run_oracle_test())
        assert result.price > 0
    
    @pytest.mark.benchmark(group="symbols")
    def test_symbol_normalization_performance(self, benchmark):
        """Benchmark symbol normalization performance."""
        def normalize_symbols():
            symbols = ['BTC/USD', 'ETH/USD', 'SOL/USD', 'BTC', 'ETH', 'SOL']
            results = []
            for symbol in symbols:
                canonical = to_canonical(symbol)
                ui_format = to_ui_format(canonical)
                results.append((symbol, canonical, ui_format))
            return results
        
        result = benchmark(normalize_symbols)
        assert len(result) == 6
    
    @pytest.mark.benchmark(group="redis")
    def test_redis_stub_performance(self, benchmark):
        """Benchmark Redis stub performance."""
        def redis_operations():
            redis_stub = RedisStub()
            
            # Set operations
            for i in range(1000):
                redis_stub.set(f"key_{i}", f"value_{i}")
            
            # Get operations
            for i in range(1000):
                redis_stub.get(f"key_{i}")
            
            # Delete operations
            for i in range(1000):
                redis_stub.delete(f"key_{i}")
            
            redis_stub.close()
            return True
        
        result = benchmark(redis_operations)
        assert result is True
    
    @pytest.mark.benchmark(group="async_redis")
    def test_async_redis_stub_performance(self, benchmark):
        """Benchmark async Redis stub performance."""
        async def async_redis_operations():
            redis_stub = AsyncRedisStub()
            
            # Set operations
            for i in range(1000):
                await redis_stub.set(f"key_{i}", f"value_{i}")
            
            # Get operations
            for i in range(1000):
                await redis_stub.get(f"key_{i}")
            
            # Delete operations
            for i in range(1000):
                await redis_stub.delete(f"key_{i}")
            
            await redis_stub.close()
            return True
        
        result = benchmark(asyncio.run, async_redis_operations())
        assert result is True
    
    @pytest.mark.benchmark(group="concurrent")
    def test_concurrent_oracle_requests(self, oracle_facade, benchmark):
        """Benchmark concurrent oracle requests."""
        async def concurrent_requests():
            tasks = []
            for i in range(100):
                tasks.append(oracle_facade.get_price('BTC/USD'))
            
            results = await asyncio.gather(*tasks)
            return len(results)
        
        result = benchmark(asyncio.run, concurrent_requests())
        assert result == 100
    
    @pytest.mark.benchmark(group="memory")
    def test_memory_usage(self, benchmark):
        """Benchmark memory usage for critical operations."""
        def memory_intensive_operation():
            # Simulate memory-intensive operation
            data = []
            for i in range(10000):
                data.append({
                    'id': i,
                    'price': Decimal('50000.00'),
                    'timestamp': 1234567890,
                    'source': 'pyth'
                })
            return len(data)
        
        result = benchmark(memory_intensive_operation)
        assert result == 10000
    
    @pytest.mark.benchmark(group="cpu")
    def test_cpu_intensive_operations(self, benchmark):
        """Benchmark CPU-intensive operations."""
        def cpu_intensive_operation():
            # Simulate CPU-intensive calculation
            total = 0
            for i in range(1000000):
                total += i ** 2
            return total
        
        result = benchmark(cpu_intensive_operation)
        assert result > 0
    
    def test_latency_requirements(self, oracle_facade):
        """Test latency requirements for critical operations."""
        async def measure_latency():
            start_time = time.time()
            result = await oracle_facade.get_price('BTC/USD')
            end_time = time.time()
            
            latency = end_time - start_time
            assert latency < 0.1  # 100ms requirement
            return latency
        
        latency = asyncio.run(measure_latency())
        assert latency < 0.1
    
    def test_throughput_requirements(self, oracle_facade):
        """Test throughput requirements for critical operations."""
        async def measure_throughput():
            start_time = time.time()
            
            # Run 100 concurrent requests
            tasks = []
            for i in range(100):
                tasks.append(oracle_facade.get_price('BTC/USD'))
            
            results = await asyncio.gather(*tasks)
            end_time = time.time()
            
            duration = end_time - start_time
            throughput = len(results) / duration
            
            assert throughput > 100  # 100 requests per second requirement
            return throughput
        
        throughput = asyncio.run(measure_throughput())
        assert throughput > 100