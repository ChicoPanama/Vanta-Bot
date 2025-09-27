# 🤖 Vanta Bot - Professional Trading Bot for Avantis Protocol

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](docker-compose.yml)
[![Base Network](https://img.shields.io/badge/Network-Base%20L2-8B5CF6.svg)](https://base.org)

> **Professional Telegram trading bot for the Avantis Protocol on Base network, featuring advanced trading capabilities, AI-powered copy trading, and enterprise-grade architecture.**

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

# Run bot
python main.py
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

### 🛡️ **Security & Reliability**
- **Encrypted Storage**: Private keys encrypted with AES-256
- **Input Validation**: Comprehensive input sanitization
- **Rate Limiting**: Protection against abuse
- **Error Handling**: Graceful degradation and recovery

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

# Blockchain
BASE_RPC_URL=https://mainnet.base.org
AVANTIS_TRADING_CONTRACT=0x...
ENCRYPTION_KEY=your_encryption_key

# Copy Trading
COPY_EXECUTION_MODE=DRY  # or LIVE
TRADER_PRIVATE_KEY=your_private_key
```

See [Configuration Guide](docs/configuration.md) for complete setup.

## 📚 **Documentation**

- **[Installation Guide](docs/installation.md)** - Complete setup instructions
- **[Configuration](docs/configuration.md)** - Environment and settings
- **[Architecture](docs/architecture.md)** - System design and structure
- **[Deployment](docs/deployment.md)** - Production setup
- **[Troubleshooting](docs/troubleshooting.md)** - Common issues and solutions
- **[API Reference](docs/api-reference.md)** - Service documentation

## 🚀 **Deployment**

### **Production Deployment**
```bash
# Using Docker Compose
docker-compose -f docker-compose.yml up -d

# Health Check
curl http://localhost:8080/healthz

# View Logs
docker-compose logs -f vanta-bot
```

### **Environment Setup**
- **Development**: Use `env.example` as template
- **Production**: Set all required environment variables
- **Monitoring**: Enable metrics and health checks

See [Deployment Guide](docs/deployment.md) for detailed instructions.

## 📊 **Monitoring & Observability**

### **Health Checks**
- **Endpoint**: `http://localhost:8080/healthz`
- **Database**: Connection and query health
- **Redis**: Cache service status
- **Blockchain**: RPC connectivity

### **Metrics**
- **Trading**: Trades executed, success rate, P&L
- **Performance**: Response times, cache hit rates
- **Users**: Active users, command usage
- **System**: Memory, CPU, database connections

### **Logging**
- **Structured Logs**: JSON format with context
- **Log Levels**: DEBUG, INFO, WARNING, ERROR
- **Rotation**: Automatic log rotation and cleanup

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

### **Key Features**
- **Encrypted Storage**: AES-256 encryption for private keys
- **Input Validation**: Comprehensive input sanitization
- **Rate Limiting**: Protection against abuse
- **SQL Injection Protection**: Parameterized queries
- **Error Handling**: Secure error responses

### **Best Practices**
- Use environment variables for secrets
- Enable HTTPS in production
- Regular security updates
- Monitor for suspicious activity

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