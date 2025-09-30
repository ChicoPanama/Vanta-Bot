# 🧪 Test Suite

This directory contains the comprehensive test suite for the Vanta Bot.

## 📋 Test Files

### Core Tests
- **[test_main.py](test_main.py)** - Main bot functionality tests
- **[test_basic.py](test_basic.py)** - Basic structure and import tests
- **[test_integration.py](test_integration.py)** - Avantis SDK integration tests

### Verification Tests
- **[test_compatibility.py](test_compatibility.py)** - Avantis Protocol compatibility tests
- **[test_final_verification.py](test_final_verification.py)** - Final verification tests
- **[verify_setup.py](verify_setup.py)** - Setup verification script

## 🚀 Running Tests

### Run All Tests
```bash
# From project root
python -m pytest tests/

# Or run individual test files
python tests/test_main.py
python tests/test_basic.py
python tests/test_integration.py
```

### Test Categories

#### 1. Basic Tests
```bash
python tests/test_basic.py
```
- Import tests
- Basic structure validation
- Configuration checks

#### 2. Main Bot Tests
```bash
python tests/test_main.py
```
- Bot initialization
- Handler registration
- Command processing

#### 3. Integration Tests
```bash
python tests/test_integration.py
```
- Avantis SDK integration
- Blockchain connectivity
- Database operations

#### 4. Compatibility Tests
```bash
python tests/test_compatibility.py
```
- Avantis Protocol compatibility
- Feature validation
- SDK method testing

#### 5. Verification Tests
```bash
python tests/test_final_verification.py
```
- End-to-end testing
- Complete functionality verification
- Production readiness checks

#### 6. Setup Verification
```bash
python tests/verify_setup.py
```
- Environment validation
- Dependencies check
- Configuration verification

## 🔧 Test Configuration

### Environment Setup
Tests require the same environment variables as the main bot:
```env
TELEGRAM_BOT_TOKEN=test_token
BASE_RPC_URL=test_rpc_url
DATABASE_URL=test_database_url
REDIS_URL=test_redis_url
ENCRYPTION_KEY=test_encryption_key
```

### Test Database
Tests use a separate test database to avoid conflicts:
```env
TEST_DATABASE_URL=postgresql://test_user:test_pass@localhost:5432/vanta_bot_test
```

## 📊 Test Coverage

The test suite covers:
- ✅ Bot initialization and configuration
- ✅ Handler registration and routing
- ✅ Database operations
- ✅ Blockchain integration
- ✅ Avantis SDK compatibility
- ✅ Security features
- ✅ Error handling
- ✅ Performance benchmarks

## 🐛 Debugging Tests

### Verbose Output
```bash
python -m pytest tests/ -v
```

### Specific Test
```bash
python -m pytest tests/test_main.py::test_bot_initialization -v
```

### Test with Coverage
```bash
pip install pytest-cov
python -m pytest tests/ --cov=src --cov-report=html
```

## 📝 Writing Tests

### Test Structure
```python
import pytest
from src.bot.handlers.start import start_handler

class TestStartHandler:
    def test_start_handler_initialization(self):
        """Test start handler initializes correctly"""
        # Test implementation
        pass

    def test_start_handler_response(self):
        """Test start handler response format"""
        # Test implementation
        pass
```

### Test Guidelines
1. Use descriptive test names
2. Test one functionality per test
3. Include docstrings for test purpose
4. Use fixtures for common setup
5. Mock external dependencies
6. Test both success and failure cases

## 🚨 Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure you're in the project root
   cd /path/to/vanta-bot
   python tests/test_basic.py
   ```

2. **Database Connection**
   ```bash
   # Check test database exists
   psql -h localhost -U test_user -d vanta_bot_test
   ```

3. **Missing Dependencies**
   ```bash
   # Install test dependencies
   pip install pytest pytest-cov pytest-asyncio
   ```

## 📈 Continuous Integration

Tests are designed to run in CI/CD pipelines:
- No external dependencies required
- Mock all external services
- Fast execution (< 30 seconds)
- Clear pass/fail indicators

## 🔄 Test Maintenance

### Regular Updates
- Update tests when adding new features
- Maintain test coverage above 80%
- Review and update test data regularly
- Keep tests fast and reliable

### Test Data
- Use realistic but anonymized data
- Avoid hardcoded values
- Use environment variables for configuration
- Clean up test data after runs

### Default test selection

Default test runs include unit and integration tests. Adhoc E2E tests under `tests/e2e/adhoc` are excluded by default. Run them explicitly:

```bash
pytest tests/e2e/adhoc -q -m "not slow"
```
