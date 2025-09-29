# Changelog

All notable changes to the Avantis Trading Bot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2024-12-19

### 🚀 Added
- **Layered Architecture**: Complete refactor with clean module boundaries
  - `src/core/`: Pure business logic with no I/O dependencies
  - `src/adapters/`: External system interfaces (Web3, Pyth, etc.)
  - `src/services/`: Business orchestration and coordination
  - `src/cli/`: Command-line interfaces for trading operations
- **Single-Scaling Invariant**: Authoritative scaling functions prevent double-scaling
  - `to_trade_units()`: Single source of truth for parameter scaling
  - `validate_scaling_consistency()`: Detects and prevents double-scaling
  - Comprehensive unit tests for scaling functions
- **Comprehensive Validation**: Multi-layer validation system
  - Human parameter validation with business rules
  - Contract limit validation against on-chain values
  - Risk management validation with configurable limits
  - Parameter clamping to safe ranges
- **CLI Tools**: Clean command-line interfaces
  - `open_trade.py`: Execute trades with human-readable parameters
  - `preflight.py`: Comprehensive validation and status checking
  - `monitor_unpaused.py`: Contract unpause monitoring
- **Address Protection**: Legacy address detection and prevention
  - `address_guard.py`: Startup validation against deprecated addresses
  - Clear error messages with remediation instructions
  - Separate current vs legacy address configurations
- **Extensive Testing**: Comprehensive test suite
  - Unit tests for core business logic (fast, isolated)
  - Integration tests for external system interactions
  - E2E tests for complete workflows (disabled by default)
  - Proper test separation with pytest markers
- **Modern Tooling**: Production-ready development tools
  - Pre-commit hooks with security scanning
  - CI/CD pipeline with automated testing
  - Code formatting with Black and isort
  - Linting with Ruff and type checking with mypy
  - Coverage reporting and security scanning

### 🔧 Changed
- **BREAKING**: Complete architecture refactor
  - All trading logic moved to layered architecture
  - SDK integration replaced with direct contract calls
  - Configuration moved to structured JSON files
- **BREAKING**: Environment configuration
  - Environment files moved to `env/` directory
  - `.env` files now properly gitignored
  - Template provided in `env/.env.example`
- **BREAKING**: Test structure
  - Tests reorganized into unit/integration/e2e
  - Integration tests require RPC access
  - E2E tests disabled by default for safety

### 🐛 Fixed
- **SDK Double-Scaling**: Resolved double-scaling issue that caused 1% slippage to become 100,000,000%
  - Root cause: SDK auto-scaling + manual pre-scaling = double-scaling
  - Solution: Direct contract calls with authoritative single scaling
  - Validation: Comprehensive tests ensure no regression
- **INVALID_SLIPPAGE Errors**: Fixed slippage validation issues
  - Problem: Double-scaled slippage exceeded contract limits
  - Solution: Proper single scaling with contract limit validation
- **BELOW_MIN_POS Errors**: Fixed position size validation
  - Problem: Incorrect position size calculations
  - Solution: Proper scaling and validation pipeline
- **Contract Integration**: Improved contract interaction reliability
  - Better error handling and decoding
  - Proper proxy address usage with implementation ABI
  - Staticcall validation before transaction execution

### 🛡️ Security
- **Secret Management**: Comprehensive secret protection
  - All secrets moved to environment variables
  - No hardcoded credentials in codebase
  - Secure key storage with envelope encryption
- **Address Validation**: Protection against deprecated addresses
  - Startup validation prevents deprecated address usage
  - Clear error messages with remediation steps
  - Separate legacy and current address configurations
- **Input Validation**: Multi-layer input validation
  - Business rule enforcement
  - Risk limit validation
  - Parameter clamping to safe ranges

### 📊 Performance
- **Faster Testing**: Unit tests run in < 1 second each
- **Parallel Execution**: Integration tests can run in parallel
- **Efficient Validation**: Optimized validation pipeline
- **Reduced Dependencies**: Direct contract calls reduce SDK overhead

### 📚 Documentation
- **Comprehensive README**: Complete setup and usage guide
- **Security Policy**: Detailed security practices and incident response
- **API Documentation**: Full API documentation with examples
- **Architecture Guide**: Detailed architecture explanation

## [2.0.0] - Previous Version

### Features
- Basic trading functionality with Avantis SDK
- Telegram bot integration
- Copy trading capabilities
- Basic risk management

### Issues
- SDK double-scaling problems
- Monolithic architecture
- Limited validation
- Basic error handling
- No address protection

## [1.0.0] - Initial Release

### Features
- Initial bot implementation
- Basic trading functionality
- Simple user interface

---

## Migration Guide

### From v2.0.0 to v2.1.0

1. **Update Environment Configuration**:
   ```bash
   # Move .env to env/.env
   mv .env env/.env
   ```

2. **Update Import Statements**:
   ```python
   # Old
   from src.blockchain.avantis_client import AvantisClient
   
   # New
   from src.services.trade_service import TradeService
   ```

3. **Update Trading Code**:
   ```python
   # Old - with SDK double-scaling issues
   sdk.open_trade(collateral, leverage, slippage)
   
   # New - with proper single scaling
   trade_service = TradeService(rpc_url, private_key)
   result = await trade_service.open_market_trade(params, dry_run=False)
   ```

4. **Update Configuration**:
   ```python
   # Old - hardcoded addresses
   TRADING_CONTRACT = "0x5FF2..."
   
   # New - structured configuration
   with open("config/addresses/base.mainnet.json") as f:
       config = json.load(f)
   trading_address = config["contracts"]["trading"]["address"]
   ```

### Breaking Changes

- **Architecture**: Complete refactor to layered architecture
- **Scaling**: SDK integration replaced with direct contract calls
- **Configuration**: Environment files moved to `env/` directory
- **Testing**: Test structure completely reorganized
- **CLI**: New command-line interfaces replace old scripts

## Success Metrics

### v2.1.0 Achievements
- ✅ **100% Unit Test Coverage**: All core business logic tested
- ✅ **Zero Double-Scaling**: Authoritative scaling prevents regression
- ✅ **Production Ready**: Comprehensive validation and error handling
- ✅ **Security Hardened**: No secrets in code, address protection
- ✅ **Developer Experience**: Modern tooling and clear documentation

### Verified Success
- **Successful Live Trade**: Transaction hash `0xebd000a15b863286e2060601b5a58073821cca71116f80ad8edca31998daead6`
- **BaseScan URL**: https://basescan.org/tx/0xebd000a15b863286e2060601b5a58073821cca71116f80ad8edca31998daead6
- **No Scaling Issues**: All parameters correctly scaled and validated
- **Clean Architecture**: Clear separation of concerns and maintainable code
- **Refactored Architecture Verified**: Core scaling functions tested and working correctly
  - ✅ Single-scaling invariant enforced (`to_trade_units()` function)
  - ✅ Parameter validation working (comprehensive validation pipeline)
  - ✅ Contract integration working (successful connection and status checks)
  - ✅ Double-scaling detection working (prevents regression)

---

**Legend**:
- 🚀 Added: New features
- 🔧 Changed: Changes to existing functionality
- 🐛 Fixed: Bug fixes
- 🛡️ Security: Security improvements
- 📊 Performance: Performance improvements
- 📚 Documentation: Documentation updates
