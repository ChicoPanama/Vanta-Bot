# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added (Phase 2: Transaction Pipeline)
- EIP-1559 transaction pipeline with type=2 transactions
- Transaction models: `TxIntent`, `TxSend`, `TxReceipt` for full lifecycle tracking
- Enhanced gas policy reading `baseFeePerGas` from latest block
- Transaction orchestrator with idempotency keys and RBF retries
- Replace-by-fee (RBF) support for stuck transactions
- Transaction builder with gas estimation and EIP-1559 support
- Nonce reconciliation helper (`make tx-reconcile`)
- Comprehensive unit and integration tests (12 passing)

### Added (Phase 1: Secrets & Safety)
- KMS-first signer with local dev fallback (`src/blockchain/signers/factory.py`)
- Envelope encryption utilities (AES-GCM + KMS) in `src/security/crypto.py`
- Encrypted SQLAlchemy types: `EncryptedBytes`, `EncryptedJSON`, `EncryptedString`
- API credentials model with envelope encryption
- Credentials repository API for encrypted secret storage
- Startup validators for signer and encryption config
- DEK rotation script (`scripts/rewrap_deks.py`) with `make rotate-deks`
- Comprehensive unit and integration tests for crypto, signers, encrypted types

### Added (Phase 0: Baseline Hygiene)
- Clean package structure with `src/vantabot/` organization
- Proper separation of production code and test/debug scripts
- Comprehensive documentation structure
- GitHub Actions CI/CD pipeline with secret scanning
- Pre-commit hooks for code quality
- Type checking with MyPy
- Code formatting with Ruff
- Phase gate scaffolding: `PHASE_STATE.md`, planning docs, PR template
- CI `phase_gate` and `verify_release` jobs; `scripts/verify_release.py`
- Python 3.11 pinned across project
- `.env.example` with placeholder configuration

### Changed
- Moved all test scripts to `tests/` directory structure
- Archived debug/experimental scripts to `tests/archive/`
- Reorganized configuration management
- Improved project hygiene and development workflow

### Security
- Enhanced security documentation
- Improved secret management guidelines
- Added vulnerability reporting process
- KMS-first signing (Phase 1: production-safe key management)
- Envelope encryption for DB secrets (AES-GCM + KMS key wrapping)
- Startup warnings for local signer usage

## [2.1.0] - 2024-01-XX

### Added
- Production-ready Avantis trading bot
- Telegram integration with advanced trading commands
- Copy trading functionality
- Risk management and position monitoring
- Multi-chain support (Base network)
- Advanced analytics and reporting
- Docker containerization
- Comprehensive monitoring and health checks

### Features
- Real-time price feeds (Chainlink, Pyth)
- Automated trading strategies
- Portfolio management
- Risk education and user onboarding
- Admin controls and monitoring
- Database persistence with SQLAlchemy
- Redis caching and coordination
- Background service management

### Security
- AES-256 encrypted private key storage
- KMS integration for production
- Rate limiting and DDoS protection
- Input validation and sanitization
- Secure configuration management

## [2.0.0] - 2024-01-XX

### Added
- Initial release of Vanta Bot
- Basic trading functionality
- Telegram bot integration
- Avantis Protocol integration

---

## Version History

- **2.1.0**: Production-ready release with full feature set
- **2.0.0**: Initial release with core functionality
- **1.x.x**: Development and testing phases (not released)
## Phase 3: Avantis SDK Hardwiring — 2025-09-30

### Added
- **Market catalog** (`src/services/markets/market_catalog.py`): Canonical registry for BTC-USD, ETH-USD, SOL-USD markets
- **Price adapters**:
  - Chainlink adapter with real on-chain price feeds
  - Pyth adapter skeleton (for Phase 7)
  - Price aggregator with fallback strategy
- **Unit normalization** (`src/blockchain/avantis/units.py`): Single-scaling rule to prevent double-scaling bugs
- **Calldata builders** (`src/blockchain/avantis/calldata.py`): ABI-encoded transaction data for openPosition/closePosition
- **AvantisService** (`src/blockchain/avantis/service.py`): Unified facade for all Avantis operations
- **UX schemas** (`src/bot/schemas/avantis.py`): Pydantic models for open/close requests
- **Startup validator** (`src/startup/markets_validator.py`): Validates market config on boot
- **Makefile target**: `make validate-markets` for config verification

### Changed
- Market catalog now loads from config with verified addresses

### Tests
- 11 new tests (8 unit, 3 integration), 100% passing
- Unit tests for normalization, calldata encoding, Chainlink adapter
- Integration tests for AvantisService validation

### Documentation
- `PHASE3_SUMMARY.md` with complete implementation details
- Docstrings on all public APIs
