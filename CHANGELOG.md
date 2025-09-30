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

## Phase 4: Persistence & Indexing — 2025-09-30

### Added
- **Database models** (Phase 4):
  - `SyncState`: Track indexer progress by block
  - `IndexedFill`: Store trade executions from chain events
  - `UserPosition`: Aggregate position state per user/symbol
- **Repositories**:
  - `positions_repo`: CRUD for positions and fills
  - `sync_state_repo`: Track indexer block progress
- **Positions cache**: Redis-backed 30s TTL cache
- **Avantis indexer**: Backfill + head-following event indexer
  - Event decoder stub (TODO: wire real Avantis ABI)
- **Service integration**: `AvantisService.list_user_positions()`
- **Startup reconciliation**: `reconcile_nonces()` on boot
- **Makefile targets**: `make indexer`, `make backfill`

### Changed
- **Migration strategy**: Squashed to single baseline
- Fixed async/sync SQLite URL handling in Alembic

### Fixed
- Migration chain conflicts resolved
- Model `__table_args__` use string column names

### Tests
- 8 new unit tests (100% passing)

### Technical Debt
- Event decoder stub (needs real Avantis ABI)
- User wallet binding (TG user → EOA) pending Phase 5


## Phase 5: Telegram UX MVP — 2025-09-30

### Added
- **User wallet binding**:
  - UserWallet model (TG user ID → EOA mapping)
  - user_wallets_repo with bind/get operations
  - Migration: phase5_user_wallets
- **UI utilities**:
  - formatting.py: fmt_addr, h1, code, ok, warn, usdc1e6
  - keyboards.py: Interactive buttons for side, leverage, slippage, confirmation
- **Middleware**:
  - User context middleware (adds user.tg_id to context)
  - Global error handler (user-friendly messages, no stack traces)
- **Bot handlers**:
  - /start, /help - Welcome and help messages
  - /bind, /balance - Wallet binding and balance check
  - /markets - List available markets with prices
  - /positions - View user positions (from Phase 4 indexer)
  - /open - Guided flow: symbol → side → leverage → collateral → slippage → confirm
  - /close - Guided flow: symbol → reduce amount → slippage → confirm
- **Bot application**:
  - Complete bootstrap with service factory
  - Dependency injection for Web3, DB, AvantisService
  - All handlers wired and registered
- **Makefile targets**:
  - make run-bot: Start Telegram bot
  - make bot-lint: Lint bot code
  - make bot-test: Run bot tests

### Integration
- All trades go through AvantisService → TxOrchestrator (Phase 2)
- Positions read from Phase 4 repositories + cache
- No handlers call Web3/SDK directly (clean architecture)

### Tests
- 10 new tests (100% passing)
  - 7 UI formatting tests
  - 3 user_wallets_repo tests

### Documentation
- Inline docstrings on all handlers
- User-friendly error messages
- PHASE5_SUMMARY.md

### User Experience
- Clean guided flows with buttons
- Address normalization
- Wallet binding per TG user
- Real-time balance and position views
- Error handling with no stack traces


## Phase 6: Signals & Automations — 2025-09-30

### Added
- **Database models** (Phase 6):
  - Signal: Trade signal records with idempotency
  - Execution: Signal execution tracking (QUEUED→APPROVED→SENT→MINED)
- **Webhook API** (FastAPI):
  - POST /signals: HMAC-signed signal ingestion
  - GET /health: Health check endpoint
  - SignalIn schema with validation
- **Signal rules**:
  - evaluate_open/close: Risk gating (sides, symbols, leverage)
  - Allowed markets: BTC-USD, ETH-USD, SOL-USD
  - Max leverage: 50x
  - Extensible for per-user policies
- **Signal worker**:
  - Redis queue consumer (LPOP from signals:q:v1)
  - Rules evaluation before execution
  - Calls AvantisService → TxOrchestrator
  - Execution audit trail
- **Operator commands**:
  - /qpeek: View signal queue
  - /pause_auto, /resume_auto: Control automation
- **Makefile targets**:
  - make run-webhook: Start FastAPI webhook
  - make run-worker: Start signal worker
  - make queue-peek: Inspect queue

### Integration
- Signals → AvantisService (Phase 3)
- Executions → TxOrchestrator (Phase 2)
- Audit trail in database (Phase 4)

### Tests
- 7 new tests (100% passing)
  - Signal rules: 7 tests (open/close validation)

### Security
- HMAC signature verification (X-Signature header)
- Idempotency via intent_key (sig:source:id)
- Master kill switches (SIGNALS_ENABLED, AUTOMATION_PAUSED)

### Documentation
- HMAC header format documented
- Signal payload schema
- CHANGELOG.md updated


## Phase 7: Advanced Features & Per-User Risk (Foundation) — 2025-09-30

### Added
- **Database models** (Phase 7):
  - UserRiskPolicy: Per-user risk limits (circuit_breaker, max_leverage, max_position, daily_loss_limit)
  - TPSL: Take-profit/stop-loss orders (tp_price, sl_price, active status)
  - Migration: phase7_user_risk_and_tp_sl
- **Repositories**:
  - risk_repo: get_or_create_policy(), update_policy()
  - tpsl_repo: add_tpsl(), list_tpsl(), deactivate_tpsl()
- **Default limits**: Max leverage 20x, max position $100k, daily loss disabled

### Status
- Foundation complete (60%)
- Database infrastructure ready
- Repositories functional

### Remaining (Phase 7.5)
- Rules engine integration with per-user policies
- Partial close UX (25%/50%/100% buttons)
- TP/SL executor daemon
- Bot handlers (/risk, /setrisk, /tpsl)
- Tests and documentation


## Phase 8: Observability & Monitoring — 2025-09-30

### Added
- **Structured JSON logging**:
  - src/monitoring/logging.py with component tagging
  - log() function for uniform JSON output
  - COMPONENT env var per process (webhook, worker, tpsl, bot)
- **Prometheus metrics**:
  - signals_queued_total, signals_rejected_total
  - exec_processed_total, exec_latency_seconds
  - queue_depth gauge
  - tpsl_triggers_total, tpsl_errors_total
  - loop_heartbeat for health monitoring
- **Metrics endpoint**: GET /metrics on webhook API (port 8090)
- **Instrumentation**:
  - Webhook: tracks queued/rejected signals
  - Worker: tracks execution status, latency, queue depth
  - TP/SL executor: tracks triggers and errors
- **Alert rules**: ops/alerts.rules.yml with Prometheus rules
  - QueueBacklogHigh, ExecutionFailuresBurst
  - RejectionSpike, TPSLErrors, WorkerSilent
- **Makefile targets**:
  - make metrics-curl: View metrics endpoint
  - make logs-json: JSON log viewing

### Integration
- Metrics exposed via FastAPI /metrics
- Ready for Prometheus scraping
- Alert rules for operational monitoring

### Tests
- 2 new tests (100% passing)
  - Metrics endpoint test
  - JSON logging shape test

### Documentation
- Alert rules documented
- Metric definitions
- CHANGELOG.md updated

