# 🤖 Vanta Bot - Production-Ready Trading Bot for Avantis Protocol

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](docker-compose.yml)
[![Base Network](https://img.shields.io/badge/Network-Base%20L2-8B5CF6.svg)](https://base.org)
[![Production Ready](https://img.shields.io/badge/Production-Ready-green.svg)](docs/production-hardening-checklist.md)

> **Enterprise-grade Telegram trading bot for the Avantis Protocol on Base network, featuring 500x leveraged trading, AI-powered copy trading, and production-hardened safety mechanisms.**

## 🚀 **Quick Start**

### **Docker (Recommended)**
```bash
# Clone and configure
git clone <repository-url>
cd avantis-telegram-bot
cp env.example .env
# Edit .env with your configuration

# Start all services
docker-compose up -d

# Check status
curl http://localhost:8080/healthz
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

## ✨ **Key Features**

### 🎯 **Core Trading**
- **80+ Trading Markets**: Crypto and Forex pairs
- **Up to 500x Leverage**: Professional-grade leverage options
- **Zero Fees**: Pay only on profitable trades
- **Real-time Execution**: Instant trade execution on Avantis Protocol

### 🤖 **AI-Powered Copy Trading**
- **Smart Leader Detection**: AI analyzes trader performance
- **Risk Management**: Automatic position sizing and risk controls
- **Performance Analytics**: Real-time P&L tracking and reporting
- **Dry Run Mode**: Test strategies without real money

### 🏗️ **Enterprise Architecture**
- **Clean Architecture**: Modular, scalable design
- **Redis Caching**: High-performance data caching
- **Background Services**: Position tracking and market indexing
- **Comprehensive Monitoring**: Health checks, metrics, and logging

### 🛡️ **Production-Grade Security & Safety**
- **Leverage Safety Manager**: Risk validation for 500x leveraged trading
- **Emergency Controls**: Global halt capabilities and maintenance modes
- **Multi-Source Price Validation**: Reliable price feeds with fallback support
- **Rate Limiting**: Redis-based user and system protection
- **Structured Logging**: Trace IDs and comprehensive audit trails
- **Health Monitoring**: Real-time system health and dependency checks
- **Task Supervision**: Automatic restart and graceful shutdown
- **Encrypted Storage**: Private keys encrypted with AES-256

## 📊 **Architecture Overview**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Telegram Bot  │    │   Web3 Layer    │    │   Database      │
│   (Handlers)    │◄──►│   (Blockchain)  │◄──►│   (PostgreSQL)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Services      │    │   Integrations  │    │   Analytics     │
│   (Business)    │◄──►│   (External)    │◄──►│   (Metrics)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### **Core Components**

- **🤖 Bot Layer**: Telegram handlers with middleware
- **⚙️ Services Layer**: Business logic and data operations  
- **🔗 Blockchain Layer**: Web3 and Avantis Protocol integration
- **📊 Data Layer**: PostgreSQL with SQLAlchemy ORM
- **🔄 Integration Layer**: External APIs and price feeds

## 🛠️ **Technology Stack**

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Backend** | Python 3.11+ | Core application |
| **Framework** | python-telegram-bot | Telegram integration |
| **Blockchain** | Web3.py, Avantis SDK | Protocol interaction |
| **Database** | PostgreSQL | Data persistence |
| **Cache** | Redis | Performance optimization |
| **Container** | Docker | Deployment |
| **Monitoring** | Custom metrics | Observability |

## 📁 **Project Structure**

```
avantis-telegram-bot/
├── src/
│   ├── bot/                    # Telegram bot components
│   │   ├── application.py      # Application factory
│   │   ├── middleware/         # Cross-cutting concerns
│   │   ├── handlers/           # Command handlers
│   │   ├── keyboards/          # UI components
│   │   └── constants.py        # Bot constants
│   ├── services/               # Business logic
│   │   ├── analytics/          # Trading analytics
│   │   ├── trading/            # Trading operations
│   │   ├── portfolio/          # Portfolio management
│   │   ├── monitoring/         # Metrics & health
│   │   └── background.py       # Service management
│   ├── blockchain/             # Web3 integration
│   ├── database/               # Data models & operations
│   ├── integrations/           # External services
│   └── utils/                  # Utilities
├── docs/                       # Documentation
├── scripts/                    # Utility scripts
├── tests/                      # Test suite
├── docker-compose.yml          # Container orchestration
└── main.py                     # Application entry point
```

## ⚙️ **Configuration**

### **Environment Variables**
```bash
# Core Configuration
TELEGRAM_BOT_TOKEN=your_bot_token
DATABASE_URL=postgresql://user:pass@localhost/db
REDIS_URL=redis://localhost:6379

# Admin Controls (Production Safety)
ADMIN_USER_IDS=123456789,987654321
SUPER_ADMIN_IDS=123456789

# Risk Management (500x Leverage Safety)
MAX_POSITION_SIZE_USD=100000
MAX_ACCOUNT_RISK_PCT=0.10
LIQUIDATION_BUFFER_PCT=0.05
MAX_DAILY_LOSS_PCT=0.20

# Blockchain
BASE_RPC_URL=https://mainnet.base.org
AVANTIS_TRADING_CONTRACT=0x...
ENCRYPTION_KEY=your_encryption_key

# Execution & Monitoring
COPY_EXECUTION_MODE=DRY  # or LIVE
DEFAULT_EXECUTION_MODE=DRY
HEALTH_PORT=8080
LOG_JSON=true  # Production logging
```

See [Configuration Guide](docs/configuration.md) for complete setup.

## 📚 **Documentation**

- **[Production Hardening Checklist](docs/production-hardening-checklist.md)** - Production readiness guide
- **[Installation Guide](docs/installation.md)** - Complete setup instructions
- **[Configuration](docs/configuration.md)** - Environment and settings
- **[Architecture](docs/architecture.md)** - System design and structure
- **[Deployment](docs/deployment.md)** - Production setup
- **[Troubleshooting](docs/troubleshooting.md)** - Common issues and solutions
- **[API Reference](docs/api-reference.md)** - Service documentation

## 🏭 **Production Deployment**

### **Production Mode (Recommended)**
```bash
# Production mode with supervision and safety features
ENVIRONMENT=production python main.py

# Health Check
curl http://localhost:8080/healthz

# Detailed readiness check
curl http://localhost:8080/readyz

# System metrics
curl http://localhost:8080/metrics
```

### **Docker Deployment**
```bash
# Using Docker Compose
docker-compose -f docker-compose.yml up -d

# Health Check
curl http://localhost:8080/healthz

# View Logs
docker-compose logs -f vanta-bot
```

### **Production Features**
- **Task Supervision**: Automatic restart with exponential backoff
- **Health Monitoring**: Real-time system health and dependency checks
- **Emergency Controls**: Global halt and maintenance mode capabilities
- **Risk Management**: 500x leverage safety validation
- **Structured Logging**: Trace IDs and comprehensive audit trails
- **Rate Limiting**: User and system protection with Redis

### **Environment Setup**
- **Development**: Use `env.example` as template
- **Production**: Set all required environment variables including admin IDs
- **Monitoring**: Enable metrics, health checks, and structured logging
- **Safety**: Configure risk management parameters and emergency controls

See [Production Hardening Checklist](docs/production-hardening-checklist.md) for complete deployment guide.

## 📊 **Monitoring & Observability**

### **Health & Monitoring Endpoints**
- **Basic Health**: `GET /healthz` - Service availability
- **Readiness Check**: `GET /readyz` - Dependency validation
- **System Metrics**: `GET /metrics` - Performance data
- **Alternative**: `GET /health` - Basic health check

### **Health Monitoring**
- **Database**: Connection and query performance
- **Redis**: Cache service status and response times
- **Blockchain**: RPC connectivity and block height
- **Price Feeds**: Multi-source validation and freshness
- **Telegram API**: Bot connectivity and authentication

### **Production Metrics**
- **Risk Management**: Position sizes, leverage usage, risk scores
- **Trading Performance**: Execution success rates, P&L tracking
- **System Performance**: CPU, memory, disk usage
- **User Activity**: Rate limiting, command usage patterns
- **Safety Events**: Emergency stops, risk limit violations

### **Structured Logging**
- **Trace IDs**: Request tracking across all components
- **JSON Format**: Production-ready structured logs
- **Context Variables**: Thread-safe trace propagation
- **Audit Trail**: All admin actions and system events logged
- **Log Levels**: DEBUG, INFO, WARNING, ERROR with rotation

## 🧪 **Testing**

```bash
# Run test suite
pytest tests/

# Run specific tests
pytest tests/test_trading.py
pytest tests/test_analytics.py

# Coverage report
pytest --cov=src tests/
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

## 🙏 **Acknowledgments**

- **Avantis Protocol** for the trading infrastructure
- **Base Network** for the L2 scaling solution
- **Open Source Community** for the amazing tools and libraries

---

**Built with ❤️ for decentralized trading on Base network.**