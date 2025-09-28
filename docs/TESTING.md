# Testing Documentation

## Overview

This document describes the comprehensive testing infrastructure for the Vanta Bot DeFi trading system.

## Test Structure

```
tests/
├── fixtures/           # Test fixtures and stubs
│   └── redis_stub.py  # In-memory Redis implementation
├── perf/              # Performance testing
│   └── test_performance.py
├── test_symbols.py    # Unit tests for symbol normalization
├── test_oracle_facade_fixed.py  # Fixed Oracle facade tests
├── test_execution_mode_redis.py # Redis integration tests
└── test_nonce_concurrency.py   # Nonce management tests
```

## Test Categories

### 1. Unit Tests
- **Symbol Normalization**: `tests/test_symbols.py`
- **Core Functions**: Basic functionality validation
- **Configuration**: Settings and environment validation

### 2. Integration Tests
- **Oracle Facade**: `tests/test_oracle_facade_fixed.py`
- **Execution Mode**: `tests/test_execution_mode_redis.py`
- **Nonce Management**: `tests/test_nonce_concurrency.py`

### 3. Performance Tests
- **Benchmarking**: `tests/perf/test_performance.py`
- **Load Testing**: `scripts/load_test_nonce.py`
- **Health Validation**: `scripts/validate_health_endpoints.py`

### 4. E2E Tests
- **Oracle System**: `scripts/test_oracle_e2e.py`
- **Complete Workflows**: End-to-end validation

## Running Tests

### Local Development
```bash
# Quick smoke test
pytest -q

# Full test suite with coverage
pytest -q --cov=src --cov-report=term-missing

# Performance tests
pytest tests/perf/ -v --benchmark-only

# Specific test categories
pytest tests/test_symbols.py -v
pytest tests/test_oracle_facade_fixed.py -v
```

### CI/CD Pipeline
```bash
# GitHub Actions runs:
pytest -q --cov=src --cov-report=term-missing --cov-fail-under=90
pytest tests/perf/ -v --benchmark-only
```

## Test Environment

### Environment Variables
```bash
ENVIRONMENT=test
LOG_JSON=false
REDIS_URL=redis://localhost:6379
DATABASE_URL=sqlite:///test.db
BASE_RPC_URL=https://mainnet.base.org
```

### Dependencies
- **pytest**: Test framework
- **pytest-asyncio**: Async test support
- **pytest-cov**: Coverage reporting
- **pytest-benchmark**: Performance testing
- **pytest-xdist**: Parallel test execution

## Test Fixtures

### Redis Stub
- **In-memory Redis**: `tests/fixtures/redis_stub.py`
- **No external dependencies**: Self-contained testing
- **Full Redis API**: Complete compatibility

### Mock Providers
- **Oracle Providers**: AsyncMock for async interfaces
- **Web3 Providers**: Mock for blockchain interactions
- **Database**: In-memory SQLite for testing

## Performance Benchmarks

### Latency Requirements
- **Oracle Requests**: < 100ms
- **Symbol Normalization**: < 1ms
- **Redis Operations**: < 10ms

### Throughput Requirements
- **Concurrent Requests**: > 100 req/s
- **Redis Operations**: > 1000 ops/s
- **Symbol Processing**: > 10000 ops/s

## Coverage Requirements

- **Minimum Coverage**: 90%
- **Critical Paths**: 100% coverage required
- **Oracle System**: Full coverage
- **Execution Mode**: Full coverage
- **Symbol Normalization**: Full coverage

## CI/CD Pipeline

### GitHub Actions
- **Matrix Testing**: Python 3.8, 3.9, 3.10, 3.11
- **Coverage Reporting**: Codecov integration
- **Performance Testing**: Benchmark validation
- **Security Scanning**: Bandit and Safety checks

### Test Stages
1. **Install Dependencies**: From requirements.txt
2. **Run Tests**: Full test suite with coverage
3. **Performance Tests**: Benchmark validation
4. **Security Scan**: Vulnerability assessment
5. **Coverage Upload**: Codecov integration

## Troubleshooting

### Common Issues
- **Redis Connection**: Use Redis stub for testing
- **Async Mock Issues**: Use AsyncMock for async methods
- **Coverage Gaps**: Add tests for uncovered code paths
- **Performance Failures**: Optimize slow operations

### Debug Mode
```bash
# Enable debug logging
ENVIRONMENT=test LOG_JSON=false pytest -v -s

# Run specific test with debug
pytest tests/test_oracle_facade_fixed.py::TestOracleFacadeFixed::test_healthy_dual_feed_operation -v -s
```

## Best Practices

### Test Writing
- **Descriptive Names**: Clear test purpose
- **Single Responsibility**: One assertion per test
- **Async Support**: Use pytest-asyncio
- **Mock External**: Use stubs for external dependencies

### Performance Testing
- **Benchmark Critical Paths**: Oracle, Redis, DB operations
- **Load Testing**: High concurrency scenarios
- **Memory Testing**: Resource usage validation
- **Latency Testing**: Response time requirements

### Coverage
- **Aim for 90%+**: Comprehensive coverage
- **Critical Paths**: 100% coverage required
- **Edge Cases**: Error handling coverage
- **Integration**: Cross-component testing

## Contributing

### Adding Tests
1. **Follow Structure**: Use existing test patterns
2. **Add Coverage**: Cover new functionality
3. **Performance**: Add benchmarks for critical paths
4. **Documentation**: Update this guide

### Test Review
- **Coverage Check**: Ensure adequate coverage
- **Performance Impact**: Validate benchmark results
- **Integration**: Test cross-component interactions
- **Documentation**: Update test documentation