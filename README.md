# 🚀 Vanta Bot - Professional Avantis Trading Bot

[![CI](https://github.com/ChicoPanama/Vanta-Bot/workflows/CI/badge.svg)](https://github.com/ChicoPanama/Vanta-Bot/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

**Production-ready Telegram trading bot for Avantis Protocol on Base network with advanced copy trading, risk management, and AI-powered insights.**

## ✨ Key Features

- 🤖 **Telegram Integration**: Intuitive bot interface with advanced trading commands
- 📈 **Copy Trading**: Follow successful traders with risk-adjusted position sizing
- 🛡️ **Risk Management**: Comprehensive position limits, slippage control, and circuit breakers
- 🔗 **Multi-Chain Support**: Native Base network integration with Avantis Protocol
- 📊 **Advanced Analytics**: Real-time portfolio tracking and performance metrics
- 🧠 **AI Insights**: Market intelligence and trading recommendations
- 🔒 **Enterprise Security**: AES-256 encryption, KMS integration, and secure key management

## 🚀 Quick Start

### Docker (Recommended)

```bash
# Clone and configure
git clone https://github.com/ChicoPanama/Vanta-Bot.git
cd Vanta-Bot
cp .env.example .env
# Edit .env with your configuration

# Start with Docker Compose
docker-compose up -d
```

### Manual Installation

```bash
# Create and activate virtualenv
python3.11 -m venv .venv && source .venv/bin/activate

# Install dependencies
pip install -U pip
pip install -e .[dev]

# Set up environment
cp .env.example .env
# Configure your settings in .env

# Run database migrations
alembic upgrade head

# Start the bot
python -m vantabot
```

## 📖 Documentation

- **[Architecture Guide](docs/architecture.md)** - System design and component overview
- **[Deployment Guide](docs/deployment.md)** - Production deployment instructions
- **[Contributing Guide](CONTRIBUTING.md)** - Development setup and guidelines
- **[Security Policy](SECURITY.md)** - Security guidelines and vulnerability reporting

## 🏗️ Project Structure

```
src/vantabot/           # Main application package
├── bot/               # Telegram bot handlers and middleware
├── services/          # Business logic and trading services
├── blockchain/        # Avantis Protocol and Web3 integration
├── database/          # Data models and repositories
├── config/            # Configuration and settings
└── utils/             # Utilities and helpers

tests/                 # Test suite
├── unit/              # Unit tests
├── integration/       # Integration tests
└── archive/           # Historical test scripts

docs/                  # Documentation
├── architecture.md    # System architecture
├── deployment.md      # Deployment guide
└── operations.md      # Operations and monitoring
```

## 🛠️ Development

### Prerequisites

- Python 3.11+ (recommended)
- PostgreSQL database
- Redis instance
- Base network RPC access

### Setup

```bash
# Install development dependencies
make install

# Run database migrations
make migrate

# Start development environment
make dev
```

### Available Commands

```bash
make help              # Show all available commands
make test              # Run unit tests
make test-all          # Run all tests including integration
make lint              # Run code linting
make format            # Format code
make typecheck         # Run type checking
make docker-build      # Build Docker image
make ci                # Run CI pipeline locally
```

## 🔧 Configuration

### Required Environment Variables

```bash
# Telegram Bot
TELEGRAM_TOKEN=your_bot_token

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/vantabot
REDIS_URL=redis://localhost:6379/0

# Blockchain
RPC_URL_BASE=https://mainnet.base.org
PRIVATE_KEY=your_private_key
```

### Optional Configuration

```bash
# Environment
ENVIRONMENT=production
DEBUG=false
DRY_RUN=false

# Risk Management
MAX_POSITION_SIZE_USD=1000
MAX_LEVERAGE=10
SLIPPAGE_TOLERANCE_BPS=50

# Feature Flags
ENABLE_COPY_TRADING=true
ENABLE_AI_INSIGHTS=false
```

See [.env.example](.env.example) for complete configuration options.

## 🚀 Deployment

### Docker Compose (Development)

```bash
docker-compose up -d
```

### Production Deployment

```bash
# Build production image
docker build -f Dockerfile.prod -t vantabot:prod .

# Deploy with production compose
docker-compose -f docker-compose.prod.yml up -d
```

### Kubernetes

See [deployment guide](docs/deployment.md) for Kubernetes deployment instructions.

## 📊 Monitoring

- **Health Check**: `GET /health`
- **Metrics**: `GET /metrics` (Prometheus format)
- **Logs**: Structured logging with correlation IDs

## 🔒 Security

- Private keys encrypted with AES-256
- KMS integration for production
- Rate limiting and DDoS protection
- Input validation and sanitization
- Secure configuration management

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/ChicoPanama/Vanta-Bot/issues)
- **Discord**: [Development Server](https://discord.gg/avantis-trading)
- **Email**: dev@avantis.trading

## ⚠️ Disclaimer

This software is for educational and research purposes. Trading cryptocurrencies involves substantial risk of loss. Use at your own risk.

---

**Built with ❤️ by the Avantis Trading Team**