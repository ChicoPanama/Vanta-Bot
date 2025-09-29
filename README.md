# 🚀 Avantis Trading Bot - Production Ready

[![CI](https://github.com/avantis-trading/avantis-telegram-bot/workflows/CI/badge.svg)](https://github.com/avantis-trading/avantis-telegram-bot/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

**Production-ready Avantis trading bot with layered architecture, single-scaling invariant, and comprehensive validation.**

## ✨ Features

- 🏗️ **Layered Architecture**: Clean separation of concerns with core domain, adapters, and services
- 🔒 **Single-Scaling Invariant**: Authoritative scaling functions prevent double-scaling issues
- 🛡️ **Comprehensive Validation**: Multi-layer validation with risk limits and business rules
- 🚀 **Production Ready**: Bulletproof error handling, logging, and monitoring
- 📊 **CLI Tools**: Clean command-line interfaces for trading operations
- 🧪 **Extensive Testing**: Unit, integration, and e2e tests with proper separation
- 🔧 **Modern Tooling**: Pre-commit hooks, CI/CD, linting, and type checking

## 🏗️ Architecture

```
src/
├── core/                # Pure business logic (no I/O)
│   ├── math.py         # Authoritative scaling functions
│   ├── models.py       # Strict data models
│   └── validation.py   # Business rules and validation
├── adapters/           # External system interfaces
│   ├── web3_trading.py # Direct contract interactions
│   ├── pyth_feed.py    # Price feed integration
│   └── address_guard.py # Legacy address protection
├── services/           # Business orchestration
│   └── trade_service.py # Complete trading flow
└── cli/               # Command-line interfaces
    ├── open_trade.py   # Trade execution CLI
    ├── preflight.py    # Validation CLI
    └── monitor_unpaused.py # Contract monitoring
```

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/avantis-trading/avantis-telegram-bot.git
cd avantis-telegram-bot

# Install dependencies
pip install -e ".[dev]"

# Set up pre-commit hooks
pre-commit install
```

### 2. Configuration

```bash
# Copy environment template
cp env/.env.example env/.env

# Edit configuration
nano env/.env
```

Required environment variables:
```bash
BASE_RPC_URL=https://mainnet.base.org
TRADER_PRIVATE_KEY=your_private_key_here
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

### 3. Validate Setup

```bash
# Run preflight check
python -m src.cli.preflight

# Run unit tests
pytest tests/unit -v

# Check linting
ruff check .
black --check .
```

### 4. Execute Trade

```bash
# Dry run (recommended first)
python -m src.cli.open_trade --collat 10 --lev 2 --slip 1 --pair 0 --long

# Live trade (when ready)
python -m src.cli.open_trade --collat 10 --lev 2 --slip 1 --pair 0 --long --live
```

## 🛠️ CLI Tools

### Open Trade
```bash
# Open a $10 long BTC position with 2x leverage and 1% slippage
python -m src.cli.open_trade --collat 10 --lev 2 --slip 1 --pair 0 --long

# Short ETH position with 5x leverage
python -m src.cli.open_trade --collat 100 --lev 5 --slip 0.5 --pair 1 --short --live
```

### Preflight Validation
```bash
# Check contract status and wallet info
python -m src.cli.preflight

# Validate specific trade parameters
python -m src.cli.preflight --collat 10 --lev 2 --slip 1 --pair 0 --long
```

### Contract Monitoring
```bash
# Monitor for contract unpause events
python -m src.cli.monitor_unpaused

# Auto-test when unpaused
python -m src.cli.monitor_unpaused --auto-test
```

## 🧪 Testing

### Unit Tests (Fast)
```bash
# Run all unit tests
pytest tests/unit -v

# Run with coverage
pytest tests/unit --cov=src --cov-report=html
```

### Integration Tests (Requires RPC)
```bash
# Run integration tests
pytest -m integration -v

# Skip integration tests
pytest --ignore-marker integration
```

### End-to-End Tests (Full Setup)
```bash
# Enable e2e tests (requires CONFIRM_SEND=YES)
export CONFIRM_SEND=YES
pytest -m e2e -v
```

## 🔒 Security

### Address Protection
The bot includes automatic protection against deprecated contract addresses:

```python
from src.adapters.address_guard import validate_contract_address

# This will raise an error if using deprecated address
validate_contract_address("0x5FF2...0535f", "trading contract")
```

### Risk Management
Built-in risk limits and validation:

- Maximum position size: $100,000 USDC
- Maximum account risk: 10%
- Maximum leverage: 500x
- Maximum slippage: 10%

## 📊 Key Improvements

### ✅ Single-Scaling Invariant
- **Before**: Double-scaling caused 1% slippage to become 100,000,000%
- **After**: Authoritative scaling functions ensure correct single scaling

### ✅ Layered Architecture
- **Before**: Monolithic code with mixed concerns
- **After**: Clean separation with core domain, adapters, and services

### ✅ Comprehensive Validation
- **Before**: Basic parameter checks
- **After**: Multi-layer validation with risk limits and business rules

### ✅ Production Hardening
- **Before**: Basic error handling
- **After**: Bulletproof error handling, logging, and monitoring

## 🔧 Development

### Code Quality
```bash
# Format code
black .
isort .

# Lint code
ruff check . --fix

# Type check
mypy src

# Run all checks
pre-commit run --all-files
```

### Adding New Features
1. Add business logic to `src/core/`
2. Add external interfaces to `src/adapters/`
3. Add orchestration to `src/services/`
4. Add CLI tools to `src/cli/`
5. Add tests to `tests/unit/`, `tests/integration/`, or `tests/e2e/`

## 📈 Monitoring

### Contract Status
```bash
# Check if trading is paused
python -m src.cli.preflight
```

### Successful Trade Logging
All successful trades are logged with:
- Transaction hash and BaseScan URL
- Exact parameters used
- Gas consumption
- Block number

## 🚨 Troubleshooting

### Common Issues

**"DEPRECATED ADDRESS DETECTED"**
- Update to use current contract addresses in `config/addresses/base.mainnet.json`

**"INVALID_SLIPPAGE"**
- Ensure slippage is in human units (1.0 for 1%), not pre-scaled
- Check that slippage doesn't exceed contract limits

**"Contract is paused"**
- Use `python -m src.cli.monitor_unpaused` to wait for unpause
- Trading will automatically resume when contract unpauses

### Debug Mode
```bash
# Enable verbose logging
python -m src.cli.open_trade --collat 10 --lev 2 --slip 1 --pair 0 --long --verbose
```

## 📝 Changelog

### v2.1.0 (2024-12-19)
- ✅ **BREAKING**: Layered architecture with clean module boundaries
- ✅ **FIX**: Single-scaling invariant prevents double-scaling issues
- ✅ **NEW**: Comprehensive validation with risk limits
- ✅ **NEW**: CLI tools for trading operations
- ✅ **NEW**: Address guard prevents deprecated address usage
- ✅ **NEW**: Extensive test suite with proper separation
- ✅ **NEW**: Modern tooling with pre-commit hooks and CI/CD

### v2.0.0 (Previous)
- Basic trading functionality
- SDK integration (with scaling issues)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run pre-commit hooks
5. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/avantis-trading/avantis-telegram-bot/issues)
- **Discussions**: [GitHub Discussions](https://github.com/avantis-trading/avantis-telegram-bot/discussions)
- **Security**: [Security Policy](SECURITY.md)

---

**⚠️ Disclaimer**: This software is for educational and research purposes. Trading involves risk. Use at your own discretion.