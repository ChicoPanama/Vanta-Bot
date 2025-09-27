# R2_PLAN.md - Phase 0: Baseline Inventory & Plan

**Goal:** Produce a precise, up-to-date blueprint of the current Vanta-Bot repo so we can implement the "tap-first" UX, quotes, allowance check, DRY→LIVE execution, risk education, resilience, and performance improvements in later phases.

**Important:** This is a read-only inventory phase. No behavior changes, only documentation.

---

## Section A — Directory Maps (actual trees)

### Root Directory (`/`)
```
avantis-telegram-bot/
├── config/                    # Configuration files
│   ├── abis/                  # Contract ABIs
│   │   ├── Trading.json       # Avantis Trading contract ABI
│   │   └── Vault.json         # Avantis Vault contract ABI
│   ├── copy_trading_schema.sql # Database schema
│   ├── init.sql               # Database initialization
│   └── vanta-bot.service      # Systemd service file
├── docs/                      # Documentation (19 files)
├── logs/                      # Log files directory
├── migrations/                # Alembic migrations
│   ├── env.py                 # Alembic environment
│   └── versions/              # Migration files
├── scripts/                   # Utility scripts (8 files)
├── src/                       # Source code
├── tests/                     # Test suite
├── main.py                    # Main entrypoint
├── requirements.txt           # Python dependencies
├── docker-compose.yml         # Docker orchestration
├── Dockerfile                 # Container definition
└── env.example               # Environment template
```

### Source Directory (`/src`)
```
src/
├── ai/                        # AI/ML components
│   ├── market_intelligence.py
│   └── trader_analyzer.py
├── analytics/                 # Analytics services
│   ├── data_extractor.py
│   └── position_tracker.py
├── blockchain/                # Web3 integration
│   ├── avantis_client.py      # Avantis protocol client
│   ├── avantis_sdk_integration.py
│   ├── base_client.py         # Base network client
│   └── wallet_manager.py      # Wallet management
├── bot/                       # Telegram bot components
│   ├── application.py         # Application factory
│   ├── constants.py           # Bot constants
│   ├── handlers/              # Command handlers (19 files)
│   ├── keyboards/             # UI components
│   ├── middleware/            # Cross-cutting concerns (5 files)
│   └── utils/                 # Bot utilities
├── config/                    # Configuration
│   ├── flags.py              # Feature flags
│   └── settings.py           # Settings management
├── copy_trading/              # Copy trading features
│   ├── copy_executor.py
│   └── leaderboard_service.py
├── database/                  # Data layer
│   ├── models.py             # SQLAlchemy models
│   └── operations.py         # Database operations
├── integrations/              # External integrations
│   └── avantis/              # Avantis SDK integration
│       ├── feed_client.py    # Price feed client
│       └── sdk_client.py     # SDK wrapper
├── middleware/                # Application middleware
│   ├── rate_limiter.py
│   └── telemetry.py
├── monitoring/                # Health & monitoring
│   ├── health_server.py      # Health endpoints
│   ├── health.py             # Health checks
│   └── performance_monitor.py
├── services/                  # Business logic services
│   ├── analytics/            # Analytics services (6 files)
│   ├── background.py          # Background service manager
│   ├── cache_service.py       # Redis caching
│   ├── contracts/             # Contract services (2 files)
│   ├── copy_trading/          # Copy trading services (3 files)
│   ├── indexers/              # Blockchain indexers (4 files)
│   ├── markets/               # Market data services (3 files)
│   ├── monitoring/            # Monitoring services (2 files)
│   ├── portfolio/             # Portfolio services (3 files)
│   ├── position_monitor.py    # Position monitoring
│   ├── price_feed_manager.py  # Price feed management
│   ├── price_service.py       # Price services
│   ├── risk_calculator.py     # Risk calculations
│   ├── risk_manager.py        # Risk management
│   └── trading/               # Trading services (4 files)
└── utils/                     # Utilities
    ├── errors.py              # Error handling
    ├── logging.py             # Logging utilities
    ├── supervisor.py          # Task supervision
    └── validators.py          # Input validation
```

### Bot Handlers (`/src/bot/handlers`)
```
handlers/
├── admin_commands.py          # Admin commands
├── admin_production_commands.py # Production admin
├── advanced_trading.py        # Advanced trading features
├── ai_insights_handlers.py    # AI insights
├── alfa_handlers.py           # Alfa leaderboard commands
├── avantis_trade_handlers.py  # Avantis trading
├── copy_trading_commands.py   # Copy trading commands
├── copytrading_handlers.py     # Copy trading handlers
├── orders.py                  # Order management
├── portfolio.py               # Portfolio handlers
├── positions.py               # Position handlers
├── registry.py                # Handler registry
├── risk_edu_handlers.py       # Risk education
├── settings.py                # Settings handlers
├── start.py                   # Start/help handlers
├── trading.py                 # Trading handlers
├── user_types.py              # User type selection
└── wallet.py                  # Wallet handlers
```

### Services Directory (`/src/services`)
```
services/
├── analytics/                 # Analytics services
│   ├── analytics.py
│   ├── fifo_pnl.py           # FIFO PnL calculations
│   ├── leaderboard_service.py # Leaderboard service
│   ├── pnl_service.py        # PnL calculations
│   └── position_tracker.py   # Position tracking
├── background.py             # Background service manager
├── base_service.py           # Base service class
├── cache_service.py          # Redis cache service
├── contracts/                 # Contract services
│   └── avantis_registry.py   # Contract registry
├── copy_trading/              # Copy trading services
│   ├── copy_executor.py      # Copy execution
│   └── execution_mode.py     # Execution modes
├── indexers/                  # Blockchain indexers
│   ├── abi_inspector.py      # ABI inspection
│   ├── avantis_indexer.py    # Avantis event indexer
│   └── run_indexer.py        # Indexer runner
├── markets/                   # Market data
│   ├── avantis_price_provider.py # Avantis price provider
│   └── price_provider.py     # Base price provider
├── monitoring/                # Monitoring services
│   └── metrics_service.py    # Metrics collection
├── portfolio/                 # Portfolio services
│   ├── portfolio_provider.py # Portfolio data provider
│   └── portfolio_service.py  # Portfolio service
├── position_monitor.py        # Position monitoring
├── price_feed_manager.py      # Price feed management
├── price_service.py           # Price services
├── risk_calculator.py         # Risk calculations
├── risk_manager.py            # Risk management
└── trading/                   # Trading services
    ├── avantis_executor.py    # Avantis execution
    ├── avantis_positions.py   # Position management
    └── trading_service.py     # Trading service
```

### Other Directories
- **`/config`**: Configuration files including ABIs
- **`/scripts`**: Utility scripts (8 files)
- **`/migrations`**: Alembic database migrations
- **`/tests`**: Test suite with copy trading tests

---

## Section B — Dependency/Runtime Inputs

### Python Version
- **Python 3.11+** (from Dockerfile and requirements.txt)

### Key Dependencies (`requirements.txt`)
```python
# Core Framework
python-telegram-bot[job-queue]==20.7  # Telegram bot framework
python-dotenv==1.0.0                   # Environment management

# Blockchain & Web3
web3>=6.0.0,<7.0.0                     # Web3.py for blockchain
eth-account>=0.8.0,<1.0.0             # Ethereum account management
avantis-trader-sdk==0.8.4             # Avantis SDK

# Database & Caching
sqlalchemy>=2.0.0,<3.0.0              # ORM
alembic>=1.10.0,<2.0.0                # Database migrations
psycopg2-binary>=2.9.0,<3.0.0         # PostgreSQL driver
redis>=4.0.0,<6.0.0                   # Redis caching

# Security & Encryption
cryptography>=40.0.0,<43.0.0          # Encryption

# AI/ML for Copy Trading
numpy>=1.21,<2                        # Numerical computing
pandas>=1.3,<2                         # Data analysis
scikit-learn>=1.0,<2                  # Machine learning

# Monitoring & Production
fastapi>=0.104.0,<1                   # Health endpoints
uvicorn>=0.24.0,<1                    # ASGI server
sentry-sdk>=1.38.0,<2                 # Error tracking
loguru>=0.7,<0.8                      # Structured logging
```

### Environment Variables (`env.example`)

#### Required Configuration
- `TELEGRAM_BOT_TOKEN` - Telegram bot token
- `ADMIN_USER_IDS` - Admin user IDs (comma-separated)
- `BASE_RPC_URL` - Base network RPC URL
- `AVANTIS_TRADING_CONTRACT` - Trading contract address
- `USDC_CONTRACT` - USDC contract address (Base USDC: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`)
- `ENCRYPTION_KEY` - 32-byte encryption key

#### Optional Configuration
- `DATABASE_URL` - Database connection (default: SQLite)
- `REDIS_URL` - Redis connection
- `PYTH_WS_URL` - Pyth price feed WebSocket
- `TRADER_PRIVATE_KEY` - Trader private key
- `AWS_KMS_KEY_ID` - AWS KMS key ID
- `COPY_EXECUTION_MODE` - DRY or LIVE mode
- `DEFAULT_SLIPPAGE_PCT` - Default slippage percentage
- `LOG_JSON` - Structured logging flag
- `HEALTH_PORT` - Health check port (8080)

---

## Section C — Entrypoint & Framework

### Main Entrypoint
- **File**: `main.py`
- **Framework**: `python-telegram-bot` v20.7 (PTB, not aiogram)
- **Application Setup**: `Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()`

### Global Startup Hooks
1. **Background Services** (`BackgroundServiceManager`)
   - Cache service initialization
   - Avantis SDK client setup
   - Price feed client startup
   - Contract registry initialization
   - Position tracker startup
   - Avantis indexer with backfill
   - Health monitoring

2. **Production Services** (when `ENVIRONMENT=production`)
   - Health server startup
   - Task supervision with exponential backoff
   - Graceful shutdown handling

---

## Section D — Handlers & Commands Map

### Command Handlers
| Command | File | Function | Description | Inline Keyboards |
|---------|------|----------|-------------|------------------|
| `/start` | `start.py` | `start_handler` | Initialize bot and wallet | ✅ User type selection |
| `/help` | `start.py` | `help_handler` | Show help message | ✅ Main menu |
| `/wallet` | `wallet.py` | `wallet_handler` | View wallet balance | ✅ |
| `/trade` | `trading.py` | `trade_handler` | Open trading interface | ✅ Direction/asset selection |
| `/positions` | `positions.py` | `positions_handler` | View open positions | ✅ |
| `/portfolio` | `portfolio.py` | `portfolio_handler` | Portfolio analytics | ✅ |
| `/orders` | `orders.py` | `orders_handler` | Order management | ✅ |
| `/settings` | `settings.py` | `settings_handler` | User settings | ✅ |
| `/analyze` | `risk_edu_handlers.py` | `cmd_analyze` | Risk analysis (education) | ❌ |
| `/calc` | `risk_edu_handlers.py` | `cmd_calc` | Position sizing calculator | ❌ |
| `/alfa` | `alfa_handlers.py` | `cmd_alfa` | Leaderboard commands | ❌ |

### Callback Query Handlers
- **Main Navigation**: `wallet`, `trade`, `positions`, `portfolio`, `orders`, `settings`, `main_menu`
- **User Type Selection**: `user_type_simple`, `user_type_advanced`, `switch_to_advanced`, `switch_to_simple`
- **Trading Flow**: `trade_long`, `trade_short`, `category_*`, `asset_*`, `leverage_*`
- **Quick Trade**: `quick_*` patterns for rapid trading
- **Advanced Features**: `close_*`, `position_sizing`, `portfolio_risk`, `performance`, `trade_history`

### Conversation Handlers
- **Trading Conversation**: Multi-step trading flow with size input and confirmation

---

## Section E — Avantis Integration Points

### Avantis SDK Client
- **File**: `src/integrations/avantis/sdk_client.py`
- **Wrapper**: `AvantisSDKClient` around `TraderClient`
- **Features**: USDC allowance checking, signer setup (local/AWS KMS)

### Price Feed Client
- **File**: `src/integrations/avantis/feed_client.py`
- **Wrapper**: `AvantisFeedClient` around `FeedClient`
- **Features**: Real-time price updates via WebSocket

### Trading Client
- **File**: `src/blockchain/avantis_client.py`
- **Features**: Position opening/closing, TP/SL management, leverage updates

### Quotes/Fees/Protection
- **Status**: **MISSING** - No quote calculation or fee estimation found
- **Target for Phase 3**: Implement quote screen with fees, protection, spread, impact

### USDC Allowance
- **Status**: **PARTIAL** - SDK client has `ensure_usdc_allowance()` method
- **Target for Phase 3**: Integrate allowance check into trading flow

### Pairs Enumeration
- **Status**: **STATIC** - Hardcoded asset lists in keyboards
- **Target for Phase 2**: Dynamic pair loading from Avantis

---

## Section F — Indexer, ABIs & Analytics

### Indexer Services
- **File**: `src/services/indexers/avantis_indexer.py`
- **Features**: Event indexing, backfill, tail following
- **Events**: TradeOpened, TradeClosed, LimitExecuted, Liquidation

### ABI Files
- **Trading ABI**: `config/abis/Trading.json` ✅ Present
- **Vault ABI**: `config/abis/Vault.json` ✅ Present

### Database Tables
- **Fills Table**: `fills` with comprehensive trading data
- **Positions Table**: `trading_positions` for position tracking
- **Copy Trading**: `copy_configurations`, `copy_positions` tables

### Analytics Services
- **Leaderboard**: `LeaderboardService` with AI-powered trader ranking
- **PnL Calculation**: FIFO PnL calculations
- **Position Tracking**: Real-time position monitoring

### Alembic Migrations
- **Files**: `2fd398e11c72_create_trader_positions_table.py`, `72287cbdfcc1_create_fills_and_positions.py`
- **Environment**: `migrations/env.py` with database URL configuration

---

## Section G — State & Persistence

### Database Stack
- **ORM**: SQLAlchemy 2.0+ with declarative models
- **Database**: PostgreSQL (production) / SQLite (development)
- **Migrations**: Alembic with proper environment configuration

### Redis Caching
- **Service**: `CacheService` for performance optimization
- **Usage**: Rate limiting, session storage, leaderboard caching

### Encryption
- **Method**: AES-256 encryption for private keys
- **Storage**: Encrypted private keys in database
- **Key Management**: Environment-based encryption key

### Tables Used
- **Users**: `users` table with wallet addresses
- **Positions**: `positions` table for open positions
- **Orders**: `orders` table for order management
- **Transactions**: `transactions` table for transaction history
- **Copy Trading**: `fills`, `trading_positions`, `copy_configurations`, `copy_positions`

---

## Section H — Background Jobs & Resilience

### Long-Running Tasks
1. **Avantis Indexer**: Event indexing with backfill and tail following
2. **Position Tracker**: Real-time position monitoring
3. **Price Feed Client**: WebSocket price updates
4. **Health Monitoring**: System health checks

### Retry/Backoff Behavior
- **Indexer**: Exponential backoff with `tenacity` library
- **WebSocket**: Reconnection logic with exponential backoff
- **Task Supervision**: Automatic restart with exponential backoff

### Health Endpoints
- **Basic Health**: `GET /healthz` - Service availability
- **Readiness**: `GET /readyz` - Dependency validation
- **Metrics**: `GET /metrics` - Performance data
- **Alternative**: `GET /health` - Basic health check

### Circuit Breaker
- **Status**: **MISSING** - No circuit breaker implementation found
- **Target for Phase 6**: Implement circuit breaker for external services

---

## Section I — Telegram UX Snapshot (Ease of Use)

### First-Run Experience (`/start`)
- **Current**: Shows welcome message with wallet creation
- **User Type Selection**: Simple vs Advanced interface choice
- **Wallet Creation**: Automatic wallet generation with encrypted private key

### Interface Types
- **Simple Interface**: Basic trading with quick trade options
- **Advanced Interface**: Professional trading tools and analytics

### Inline Keyboards Usage
- **Main Menu**: 6-button layout (Wallet, Trade, Positions, Orders, Portfolio, Settings)
- **Trading Flow**: Multi-step selection (Direction → Category → Asset → Leverage)
- **Quick Trade**: One-tap trading for major assets

### Formatting Quality
- **Markdown**: Proper markdown formatting for messages
- **Emojis**: Consistent emoji usage for visual clarity
- **Pagination**: Message splitting for long content

### Zero-Typing Flows
- **Current**: Multi-step button navigation
- **Missing**: One-tap execution flows
- **Target for Phase 2**: Implement tap-first UX with pair sheets

---

## Section J — Risk/Education

### Risk Education Features
- **Commands**: `/analyze` and `/calc` for risk education
- **Status**: **PRESENT** - Non-blocking risk education
- **Features**: Risk level assessment, scenario analysis, position sizing suggestions

### DRY/LIVE Toggle
- **Status**: **PRESENT** - `COPY_EXECUTION_MODE` environment variable
- **Enforcement**: Global setting, not per-chat
- **Target for Phase 4**: Per-chat DRY/LIVE toggle with admin controls

### Risk Management
- **Calculator**: `RiskCalculator` with comprehensive risk analysis
- **Warnings**: Educational warnings for high-risk positions
- **Limits**: Position size limits and leverage validation

---

## Section K — Observability & CI

### Logging Style
- **Framework**: `loguru` for structured logging
- **Format**: JSON logging in production (`LOG_JSON=true`)
- **Trace IDs**: Request tracking across components
- **Fields**: User IDs (hashed), operation context, error details

### Health Commands
- **Status**: **PRESENT** - Comprehensive health monitoring
- **Endpoints**: `/healthz`, `/readyz`, `/metrics`
- **Checks**: Database, Redis, price feeds, blockchain, Telegram API

### CI/CD
- **Status**: **MISSING** - No GitHub Actions found
- **Target for Phase 1**: Implement CI/CD pipeline

### Code Quality
- **Status**: **MISSING** - No pre-commit hooks found
- **Target for Phase 1**: Implement pre-commit hooks and code formatting

---

## Findings: Gaps vs Goals

| Area | Current | Target |
|------|---------|--------|
| **Onboarding** | Basic `/start` with wallet creation | Big buttons: Markets / Quick Trade / Positions |
| **Quick Trade** | Multi-step button navigation | Pair Sheet → Long/Short → leverages/collateral chips → Confirm |
| **Quotes** | **MISSING** | Fee + Protection + Spread/Impact + Slippage on confirm |
| **Allowance** | SDK method exists but not integrated | One-tap "Approve USDC" before execution |
| **DRY/LIVE** | Global environment variable | Always visible chip; admin toggle |
| **Positions UX** | Basic position display | One-tap Close 25/50/100% |
| **Risk** | `/analyze` and `/calc` commands | `/analyze` + `/calc` + "View Risk" (non-blocking) |
| **Resilience** | Basic health checks | Supervised tasks + `/status` health |
| **Performance** | Basic Redis caching | DB indexes + leaderboard caching |
| **Docs** | Basic `/help` command | Crisp `/help`, Runbook, Risk EDU |

---

## Phase-by-Phase TODO Checklist

- [ ] **Phase 1:** Tooling & settings (pyproject, pre-commit, CI, logger)
- [ ] **Phase 2:** Tap-first UX (`/start`, `/markets`, Pair Sheet, Quick Trade)
- [ ] **Phase 3:** Quote screen + allowance check + slippage (no surprises)
- [ ] **Phase 4:** Execution (DRY→LIVE), `/positions` with 25/50/100% close
- [ ] **Phase 5:** Risk education (`/analyze`, `/calc`, inline "View Risk")
- [ ] **Phase 6:** Resilience & observability (supervisor, logs, `/status`)
- [ ] **Phase 7:** Performance (DB indexes + Redis caching for leaderboard)
- [ ] **Phase 8:** UX polish & docs

---

## Sanity Check

✅ **All handler files enumerated** with correct paths (19 handler files)
✅ **Avantis SDK usage points identified** (SDK client, feed client, trading client)
✅ **ABI file presence confirmed** (`config/abis/Trading.json`, `config/abis/Vault.json`)
✅ **Indexer and DB tables/migrations listed** (Alembic migrations, comprehensive table structure)
✅ **Env variables mapped** and cross-referenced with `env.example` (172 lines of configuration)
✅ **No aiogram code paths** - Confirmed using `python-telegram-bot` v20.7

**Repository Status**: Production-ready codebase with comprehensive features, ready for Phase 1 implementation.
