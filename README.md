# 🚀 Vanta Bot - Enterprise-Grade DeFi Trading Bot

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](docker-compose.yml)
[![Base Network](https://img.shields.io/badge/Network-Base%20L2-8B5CF6.svg)](https://base.org)
[![Enterprise Ready](https://img.shields.io/badge/Enterprise-Ready-green.svg)](ENTERPRISE_DEPLOYMENT.md)
[![Security](https://img.shields.io/badge/Security-Envelope%20Encryption-red.svg)](src/security/)
[![Monitoring](https://img.shields.io/badge/Monitoring-Prometheus-orange.svg)](src/monitoring/)

> **Enterprise-grade DeFi trading bot with bank-level security, comprehensive monitoring, and production-ready reliability for high-volume trading operations.**

## 🚀 **Quick Start**

### **Enterprise Deployment (Recommended)**
```bash
# Clone and configure
git clone <repository-url>
cd avantis-telegram-bot
cp env.example .env
# Edit .env with your enterprise configuration

# Run enterprise deployment
python scripts/deploy_enterprise.py

# Check health
curl http://localhost:8080/health
curl http://localhost:8080/ready
curl http://localhost:8080/metrics
```

### **Docker Deployment**
```bash
# Start all services
docker-compose up -d

# Check status
curl http://localhost:8080/health
```

### **Manual Installation**
```bash
# Install dependencies
pip install -r requirements.txt

# Setup database
createdb vanta_bot
alembic upgrade head

# Run bot (development mode)
python main.py

# Run bot (production mode with supervision)
ENVIRONMENT=production python main.py
```

## 📱 **Bot Commands**

### **Getting Started**
- `/start` - Welcome message and first-run tour
- `/help` - Quick command reference and usage guide
- `/markets` - Browse available trading pairs with user preferences

### **Trading**
- `/positions` - View and manage your open positions
- `/analyze` - Educational risk analysis (Phase 5)
- `/calc` - Position size calculator and helper

### **User Settings**
- `/prefs` - Configure default slippage, leverage chips, collateral chips, and favorites
- `/mode` - Set UI preference (DRY/LIVE) - *server controls actual execution mode*
- `/linkwallet` - Link EVM address for read-only analytics (optional)

### **Copy-Trading**
- `/alfa top50` - View top traders with Follow buttons for easy copy-trading setup
- `/follow <trader_id>` - Follow a trader and configure copy settings
- `/following` - Manage your followed traders and their copy settings
- `/unfollow <trader_id>` - Stop following a trader

### **Admin Commands**
- `/autocopy_off_all` - Emergency disable auto-copy for all users
- `/autocopy_on_user <id>` - Enable auto-copy for specific user
- `/autocopy_off_user <id>` - Disable auto-copy for specific user

### **System & Admin**
- `/health` - System health and uptime status
- `/diag` - Diagnostic information and circuit status

> **Note**: All user preferences are optional and stored locally. The `/mode` command sets your UI preference only - actual execution mode is controlled by server configuration for safety.

## ✨ **Enterprise Features**

### 🔐 **Bank-Level Security**
- **Envelope Encryption**: Per-wallet DEKs protected by AWS KMS
- **Key Rotation**: Zero-downtime key rotation with automatic re-encryption
- **Access Control**: Role-based permissions with admin/super-admin tiers
- **Rate Limiting**: Token bucket rate limiting with Redis
- **Input Validation**: Pydantic schema validation for all commands
- **Security Redaction**: Automatic redaction of sensitive data in logs

### ⚡ **Advanced Transaction Pipeline**
- **Nonce Management**: Redis-based nonce reservation with distributed locks
- **Gas Optimization**: EIP-1559 gas policy with surge protection and caps
- **Idempotency**: Request ID-based duplicate transaction prevention
- **Retry Logic**: Exponential backoff with jitter for failed transactions
- **Circuit Breakers**: Automatic failure protection for external services
- **Private Transactions**: MEV protection via private mempool support

### 🎯 **Core Trading**
- **80+ Trading Markets**: Crypto and Forex pairs
- **Up to 500x Leverage**: Professional-grade leverage options
- **Zero Fees**: Pay only on profitable trades
- **Real-time Execution**: Instant trade execution on Avantis Protocol
- **Slippage Protection**: Configurable slippage bounds with oracle validation
- **Risk Management**: Comprehensive position sizing and liquidation monitoring

### 🤖 **AI-Powered Copy Trading**
- **Smart Leader Detection**: AI analyzes trader performance with `/alfa top50`
- **One-Tap Follow**: Follow top traders directly from leaderboard
- **Per-Trader Settings**: Configure auto-copy, sizing modes, risk caps, and notifications
- **Risk Management**: Automatic position sizing, leverage caps, and loss protection
- **Trade Alerts**: Get notified when followed traders open/close positions
- **Daily Digests**: Summary of followed traders' performance and activity
- **Enhanced AI Models**: Updated clustering algorithms and market intelligence

### 🏗️ **Enterprise Architecture**
- **Clean Architecture**: Modular, scalable design with dependency injection
- **Redis Caching**: High-performance data caching with connection pooling
- **Background Services**: Position tracking and market indexing
- **Comprehensive Monitoring**: Health checks, metrics, and structured logging
- **Database Optimization**: High-precision numeric types and performance indexes
- **Service Mesh**: Circuit breakers and health monitoring for all services

### 📊 **Advanced Monitoring & Observability**
- **Health Endpoints**: `/live`, `/ready`, `/health` with comprehensive checks
- **Prometheus Metrics**: Transaction, wallet, oracle, and system metrics
- **Structured Logging**: JSON logging with security redaction
- **Circuit Breaker Monitoring**: Real-time service health tracking
- **Performance Metrics**: Database, Redis, and RPC performance monitoring
- **Risk Metrics**: Position risk scores and liquidation monitoring

## 📊 **Enterprise Architecture**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Telegram Bot  │    │   Security      │    │   Monitoring    │
│   (Handlers)    │◄──►│   (Key Vault)   │◄──►│   (Health)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Transaction   │    │   Web3 Layer    │    │   Database      │
│   Pipeline      │◄──►│   (Blockchain)  │◄──►│   (PostgreSQL)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Risk Engine   │    │   Oracle        │    │   Analytics     │
│   (Validation)  │◄──►│   (Price Feeds) │◄──►│   (Metrics)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### **Enterprise Components**

- **🔐 Security Layer**: Envelope encryption, key rotation, access control
- **⚡ Transaction Pipeline**: Nonce management, gas optimization, retry logic
- **🤖 Bot Layer**: Rate limiting, authorization, command validation
- **📊 Risk Engine**: Position validation, liquidation monitoring, portfolio risk
- **🔗 Blockchain Layer**: Web3 integration with circuit breakers
- **📈 Monitoring**: Health checks, metrics, structured logging
- **🗄️ Data Layer**: High-precision numeric types with performance indexes

## 🛠️ **Enterprise Technology Stack**

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Backend** | Python 3.11+ | Core application |
| **Framework** | python-telegram-bot | Telegram integration |
| **Blockchain** | Web3.py, Avantis SDK | Protocol interaction |
| **Security** | AWS KMS, Cryptography | Envelope encryption |
| **Database** | PostgreSQL | High-precision data persistence |
| **Cache** | Redis | Nonce management & caching |
| **Monitoring** | Prometheus, FastAPI | Metrics & health monitoring |
| **Validation** | Pydantic | Schema validation |
| **Container** | Docker | Deployment |
| **CI/CD** | GitHub Actions | Automated testing |

## ✅ **Enterprise QA Status (2025-01-01)**

- **Security Tests**: ✅ Envelope encryption, key rotation, and access control
- **Transaction Pipeline**: ✅ Nonce management, gas optimization, and retry logic
- **Risk Engine**: ✅ Position validation, liquidation monitoring, and portfolio risk
- **Monitoring**: ✅ Health checks, metrics, and circuit breaker status
- **Database**: ✅ High-precision numeric types and performance indexes
- **Integration**: ✅ Avantis SDK, Web3 pipeline, and oracle aggregation
- **Testing Coverage**: ✅ Comprehensive unit and integration tests
- **Production Ready**: ✅ All enterprise features deployed and validated

## 📁 **Enterprise Project Structure**

```
avantis-telegram-bot/
├── src/
│   ├── security/              # 🔐 Security & encryption
│   │   └── key_vault.py       # Envelope encryption
│   ├── blockchain/            # ⚡ Web3 & transaction pipeline
│   │   ├── tx/                # Transaction pipeline
│   │   │   ├── nonce_manager.py
│   │   │   ├── gas_policy.py
│   │   │   ├── builder.py
│   │   │   └── sender.py
│   │   └── abi_loader.py      # ABI management
│   ├── services/              # 📊 Business logic & risk
│   │   ├── oracle.py          # Price aggregation
│   │   └── risk/              # Risk engine
│   │       └── primitives.py  # Financial calculations
│   ├── monitoring/            # 📈 Observability
│   │   ├── health_server.py   # Health endpoints
│   │   ├── logging.py         # Structured logging
│   │   └── metrics.py         # Prometheus metrics
│   ├── middleware/            # 🔄 Cross-cutting concerns
│   │   └── circuit_breakers.py
│   ├── bot/                   # 🤖 Telegram bot
│   │   ├── middleware/        # Rate limiting & auth
│   │   └── schemas.py         # Command validation
│   ├── database/              # 🗄️ Data layer
│   │   └── transaction_repo.py
│   └── config/                # ⚙️ Configuration
├── tests/                     # 🧪 Comprehensive testing
│   ├── security/             # Security tests
│   ├── blockchain/           # Pipeline tests
│   └── risk/                 # Risk engine tests
├── scripts/                   # 🚀 Deployment scripts
│   └── deploy_enterprise.py  # Enterprise deployment
├── migrations/               # 🗄️ Database migrations
├── docs/                     # 📚 Documentation
├── ENTERPRISE_DEPLOYMENT.md  # 🚀 Enterprise guide
└── main.py                   # Application entry point
```

## ⚙️ **Enterprise Configuration**

### **Required Environment Variables**
```bash
# Core Configuration
TELEGRAM_BOT_TOKEN=your_bot_token
DATABASE_URL=postgresql://user:pass@localhost/db
REDIS_URL=redis://localhost:6379
BASE_RPC_URL=https://mainnet.base.org

# Security (Choose one)
# Option 1: AWS KMS (Production)
AWS_KMS_KEY_ID=arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012
AWS_REGION=us-east-1

# Option 2: Local Key Vault (Development)
LOCAL_WRAP_KEY_B64=your_base64_encoded_key

# Feature Flags
KEY_ENVELOPE_ENABLED=true
TX_PIPELINE_V2=true
AVANTIS_V2=true
STRICT_HANDLERS_ENABLED=true
STRUCTURED_LOGS_ENABLED=true

# Admin Controls
ADMIN_USER_IDS=123456789,987654321
SUPER_ADMIN_IDS=123456789

# Monitoring
ENABLE_METRICS=true
HEALTH_PORT=8080
LOG_LEVEL=INFO
LOG_JSON=true
```

### **Optional Configuration**
```bash
# Avantis Integration
AVANTIS_TRADING_CONTRACT=0x...
AVANTIS_VAULT_CONTRACT=0x...
USDC_CONTRACT=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913

# Trading Limits
MAX_LEVERAGE=500
MAX_POSITION_SIZE=100000
MIN_POSITION_SIZE=1
DEFAULT_SLIPPAGE_PCT=1.0

# Rate Limiting
COPY_EXECUTION_RATE_LIMIT=10
TELEGRAM_MESSAGE_RATE_LIMIT=30
```

See [Enterprise Deployment Guide](ENTERPRISE_DEPLOYMENT.md) for complete setup.

## 📚 **Enterprise Documentation**

- **[Enterprise Deployment Guide](ENTERPRISE_DEPLOYMENT.md)** - Complete enterprise setup
- **[Production Hardening Checklist](docs/production-hardening-checklist.md)** - Production readiness guide
- **[Installation Guide](docs/installation.md)** - Complete setup instructions
- **[Configuration](docs/configuration.md)** - Environment and settings
- **[Architecture](docs/architecture.md)** - System design and structure
- **[Security Guide](docs/security.md)** - Security best practices
- **[Monitoring Guide](docs/monitoring.md)** - Observability setup
- **[Troubleshooting](docs/troubleshooting.md)** - Common issues and solutions

## 🏭 **Enterprise Deployment**

### **Enterprise Deployment (Recommended)**
```bash
# Run enterprise deployment script
python scripts/deploy_enterprise.py

# Health Checks
curl http://localhost:8080/live    # Liveness probe
curl http://localhost:8080/ready   # Readiness probe
curl http://localhost:8080/health  # Comprehensive health
curl http://localhost:8080/metrics # Prometheus metrics
```

### **Docker Deployment**
```bash
# Using Docker Compose
docker-compose -f docker-compose.yml up -d

# Health Check
curl http://localhost:8080/health

# View Logs
docker-compose logs -f vanta-bot
```

### **Enterprise Features**
- **🔐 Envelope Encryption**: Per-wallet DEKs protected by AWS KMS
- **⚡ Transaction Pipeline**: Nonce management, gas optimization, retry logic
- **🛡️ Security**: Rate limiting, access control, input validation
- **📊 Risk Engine**: Position validation, liquidation monitoring
- **📈 Monitoring**: Health checks, metrics, circuit breakers
- **🗄️ Database**: High-precision numeric types with performance indexes
- **🔄 Observability**: Structured logging, tracing, metrics

### **Environment Setup**
- **Development**: Use `env.example` as template with local key vault
- **Production**: Configure AWS KMS, admin IDs, and feature flags
- **Monitoring**: Enable Prometheus metrics and structured logging
- **Security**: Configure envelope encryption and access controls

See [Enterprise Deployment Guide](ENTERPRISE_DEPLOYMENT.md) for complete setup.

## 📊 **Enterprise Monitoring & Observability**

### **Health Endpoints**
- **Liveness**: `GET /live` - Service availability
- **Readiness**: `GET /ready` - Dependency validation
- **Health**: `GET /health` - Comprehensive system health
- **Metrics**: `GET /metrics` - Prometheus metrics

### **Health Monitoring**
- **Database**: Connection, query performance, and migration status
- **Redis**: Cache service status, nonce management, and response times
- **Blockchain**: RPC connectivity, block height, and transaction status
- **Oracle**: Price feed validation, freshness, and deviation monitoring
- **Circuit Breakers**: Service health and failure protection status
- **Key Vault**: Encryption/decryption operations and key rotation status

### **Enterprise Metrics**
- **Security**: Wallet encryption errors, key rotation status, access control
- **Transactions**: Send success rates, confirmation times, retry counts
- **Risk Management**: Position risk scores, liquidation monitoring, portfolio risk
- **System Performance**: Database, Redis, and RPC performance metrics
- **User Activity**: Rate limiting, command usage, authorization events
- **Business Metrics**: Trading volume, P&L tracking, copy trading performance

### **Structured Logging**
- **Security Redaction**: Automatic redaction of sensitive data
- **JSON Format**: Production-ready structured logs with context
- **Trace IDs**: Request tracking across all components
- **Audit Trail**: All admin actions, security events, and system changes
- **Log Levels**: DEBUG, INFO, WARNING, ERROR with rotation
- **Context Variables**: Thread-safe trace propagation and correlation

## 🧪 **Enterprise Testing**

### **Comprehensive Test Suite**
```bash
# Run all tests
pytest tests/

# Run specific test suites
pytest tests/security/     # Security & encryption tests
pytest tests/blockchain/    # Transaction pipeline tests
pytest tests/risk/          # Risk engine tests

# Coverage report
pytest --cov=src tests/
```

### **Security Testing**
```bash
# Test envelope encryption
pytest tests/security/test_key_vault.py -v

# Test encryption roundtrips
pytest tests/security/ -k "encrypt" -v
```

### **Integration Testing**
```bash
# Test transaction pipeline
pytest tests/blockchain/test_tx_pipeline.py -v

# Test risk calculations
pytest tests/risk/test_primitives.py -v
```

## 🧪 **Testing & Monitoring**

### **Unit Tests**
```bash
# Run all tests
make test

# Run copy-trading tests
pytest tests/test_copy_store.py
pytest tests/test_copy_service.py
pytest tests/test_alerts.py

# Run with coverage
pytest --cov=src tests/
```

### **SDK Validation**
```bash
# Check Avantis SDK setup and connectivity
python scripts/check_avantis_sdk.py

# Expected output: ✅ All SDK checks passed (with proper API keys)
```

### **Synthetic Signal Monitoring**
```bash
# Run synthetic health check (sends test signal to ops chat)
python scripts/synthetic_signal_cron.py

# Expected output: ✅ Synthetic signal check passed
```

### **Production Validation**
```bash
# Run comprehensive validation
python scripts/validate_phase8.py

# Run final mile tests
python scripts/test_final_mile.py
```

### **Feature Flags**
```bash
# Environment variables for controlled rollout
export COPY_AUTOCOPY_DEFAULT=off          # Default auto-copy setting
export AUTOCOPY_ALLOWLIST=12345678,98765432  # Allowed user IDs
export REDIS_URL=redis://localhost:6379   # Optional Redis for deduplication
```

## 🔒 **Security**

### **Production Safety Features**
- **Leverage Safety Manager**: Risk validation for 500x leveraged trading
- **Emergency Controls**: Global halt capabilities and maintenance modes
- **Multi-Source Price Validation**: Prevents price manipulation attacks
- **Rate Limiting**: Redis-based protection against abuse
- **Admin Permissions**: Role-based access control with audit trails
- **Task Supervision**: Automatic restart and graceful shutdown
- **Encrypted Storage**: AES-256 encryption for private keys
- **Input Validation**: Comprehensive input sanitization
- **SQL Injection Protection**: Parameterized queries

### **Risk Management**
- **Position Limits**: Maximum $100,000 per position
- **Account Risk**: Maximum 10% account risk per position
- **Liquidation Buffer**: 5% buffer before liquidation
- **Daily Loss Limits**: Maximum 20% daily loss protection
- **Leverage Validation**: Up to 500x with safety checks

### **Best Practices**
- Configure admin user IDs before deployment
- Use environment variables for all secrets
- Enable structured JSON logging in production
- Monitor health endpoints continuously
- Regular security updates and dependency checks
- Test emergency controls in staging environment

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

See [Contributing Guide](docs/contributing.md) for detailed guidelines.

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 **Support**

- **Documentation**: Check the [docs/](docs/) directory
- **Issues**: Report bugs via GitHub Issues
- **Discussions**: Join community discussions
- **Security**: Report security issues privately

## 🔄 **Enterprise Updates**

### **Enterprise Transformation (Latest)**
- ✅ **Bank-Level Security**: Envelope encryption with per-wallet DEKs and AWS KMS integration
- ✅ **Advanced Transaction Pipeline**: Nonce management, gas optimization, and retry logic
- ✅ **Comprehensive Risk Engine**: Position validation, liquidation monitoring, and portfolio risk
- ✅ **Enterprise Monitoring**: Health checks, Prometheus metrics, and circuit breakers
- ✅ **Production Database**: High-precision numeric types with performance indexes
- ✅ **Security Hardening**: Rate limiting, access control, and input validation

### **Enterprise Features**
- ✅ **Envelope Encryption**: Per-wallet DEKs protected by AWS KMS with zero-downtime rotation
- ✅ **Transaction Pipeline**: Redis-based nonce management with EIP-1559 gas optimization
- ✅ **Risk Management**: Comprehensive position validation and liquidation monitoring
- ✅ **Monitoring**: Health endpoints, Prometheus metrics, and structured logging
- ✅ **Security**: Rate limiting, authorization, and security redaction
- ✅ **Database**: High-precision numeric types with performance optimization

## 🙏 **Acknowledgments**

- **Avantis Protocol** for the trading infrastructure
- **Base Network** for the L2 scaling solution
- **Open Source Community** for the amazing tools and libraries

---

**Built with ❤️ for decentralized trading on Base network.**