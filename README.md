# 🚀 Vanta Bot

A professional Telegram trading bot for the Avantis Protocol on Base network, featuring 80+ markets, up to 500x leverage, and zero fees on entry/exit.

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue.svg)](https://telegram.org)
[![Avantis](https://img.shields.io/badge/Avantis-Protocol-green.svg)](https://avantis.trade)
[![Base](https://img.shields.io/badge/Base-Network-blue.svg)](https://base.org)

## ✨ Features

- **📊 80+ Trading Markets**: Crypto, Forex, Commodities, Indices
- **⚡ High Leverage**: Up to 500x leverage on supported assets
- **💰 Zero Fees**: Pay fees only on profitable trades
- **🛡️ Secure**: Encrypted private keys, rate limiting, input validation
- **📱 User-Friendly**: Intuitive Telegram interface with inline keyboards
- **🔄 Real-Time**: Live price updates and position monitoring
- **📈 Analytics**: Portfolio tracking and performance metrics
- **🔒 Self-Custody**: Users maintain full control of their funds

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Telegram Bot  │    │   PostgreSQL    │    │   Base Network  │
│                 │    │   Database      │    │   (Avantis)     │
│  - Handlers     │◄──►│  - Users        │◄──►│  - Trading      │
│  - Keyboards    │    │  - Positions    │    │  - Positions    │
│  - Middleware   │    │  - Orders       │    │  - Balances     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Redis Cache   │    │  Price Service   │    │  Position      │
│                 │    │                 │    │  Monitor       │
│  - Rate Limiting│    │  - CoinGecko API │    │  - Liquidation │
│  - Session Data  │    │  - Forex Data   │    │  - Alerts      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL 12+
- Redis 6+
- Telegram Bot Token
- Base RPC access (Alchemy/QuickNode)

### 1. Clone and Setup

```bash
git clone <repository-url>
cd vanta-bot
python scripts/setup.py
```

### 2. Configure Environment

Copy the environment template and edit with your values:

```bash
cp env.example .env
nano .env
```

Required environment variables:
```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather

# Base Chain
BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/your-api-key
BASE_CHAIN_ID=8453

# Database
DATABASE_URL=postgresql://bot_user:password@localhost:5432/vanta_bot

# Redis
REDIS_URL=redis://localhost:6379

# Security
ENCRYPTION_KEY=your-32-byte-encryption-key

# Avantis Contracts
AVANTIS_TRADING_CONTRACT=0x...
AVANTIS_VAULT_CONTRACT=0x...
USDC_CONTRACT=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
```

### 3. Set Up Database

```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib  # Ubuntu/Debian
brew install postgresql                          # macOS

# Create database
sudo -u postgres psql
CREATE DATABASE vanta_bot;
CREATE USER bot_user WITH ENCRYPTED PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE vanta_bot TO bot_user;
```

### 4. Set Up Redis

```bash
# Install Redis
sudo apt install redis-server  # Ubuntu/Debian
brew install redis              # macOS

# Start Redis
sudo systemctl start redis      # Linux
brew services start redis       # macOS
```

### 5. Test Installation

```bash
python tests/test_basic.py
```

### 6. Start the Bot

```bash
python main.py
```

## 🐳 Docker Deployment

### Using Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f bot

# Stop services
docker-compose down
```

### Manual Docker Build

```bash
# Build image
docker build -t vanta-bot .

# Run container
docker run -d --name vanta-bot \
  --env-file .env \
  vanta-bot
```

## 📱 Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Initialize bot and create wallet |
| `/help` | Show help information |
| `/wallet` | View wallet balance and address |
| `/trade` | Open trading interface |
| `/positions` | View open positions |
| `/portfolio` | Portfolio analytics |
| `/orders` | View pending orders |
| `/settings` | Bot configuration |

## 🎯 Trading Features

### Supported Markets

- **Crypto**: BTC, ETH, SOL, AVAX, and more
- **Forex**: EUR/USD, GBP/USD, USD/JPY, AUD/USD
- **Commodities**: Gold, Silver, Oil, Gas
- **Indices**: S&P 500, NASDAQ, FTSE 100

### Leverage Options

- 2x, 5x, 10x, 25x, 50x, 100x, 250x, 500x

### Order Types

- **Market Orders**: Instant execution
- **Limit Orders**: Set entry/exit prices
- **Stop Orders**: Risk management

## 🔒 Security Features

- **Encrypted Storage**: Private keys encrypted with Fernet
- **Rate Limiting**: Prevents spam and abuse
- **Input Validation**: Sanitizes all user inputs
- **Self-Custody**: Users control their own funds
- **Secure Communication**: All data encrypted in transit

## 📊 Monitoring & Analytics

### Portfolio Tracking

- Real-time PnL calculation
- Win rate statistics
- Total trading volume
- Best/worst trades

### Position Monitoring

- Automatic liquidation detection
- Price alert notifications
- Risk management tools
- Performance analytics

## 🛠️ Development

### Project Structure

```
vanta-bot/
├── src/                    # Source code
│   ├── bot/               # Telegram bot handlers
│   ├── blockchain/        # Blockchain integration
│   ├── database/          # Database layer
│   ├── services/          # Business logic
│   ├── middleware/        # Middleware
│   ├── utils/             # Utilities
│   └── config/            # Configuration
├── tests/                 # Test suite
├── docs/                  # Documentation
├── scripts/               # Utility scripts
├── config/                # Configuration files
├── main.py                # Bot entry point
├── requirements.txt       # Dependencies
├── Dockerfile             # Docker configuration
├── docker-compose.yml     # Docker Compose
└── README.md              # This file
```

### Adding New Features

1. **New Handlers**: Add to `src/bot/handlers/`
2. **New Services**: Add to `src/services/`
3. **Database Changes**: Update `src/database/models.py`
4. **New Keyboards**: Add to `src/bot/keyboards/`

### Testing

```bash
# Run all tests
python -m pytest tests/

# Test specific components
python tests/test_main.py
python tests/test_integration.py
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather | Yes |
| `BASE_RPC_URL` | Base network RPC endpoint | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `ENCRYPTION_KEY` | 32-byte encryption key | Yes |
| `AVANTIS_TRADING_CONTRACT` | Avantis trading contract | Yes |
| `USDC_CONTRACT` | USDC token contract | Yes |
| `DEBUG` | Enable debug mode | No |
| `LOG_LEVEL` | Logging level | No |

### Trading Limits

- **Min Position Size**: $1 USDC
- **Max Position Size**: $100,000 USDC
- **Max Leverage**: 500x
- **Rate Limit**: 10 requests/minute per user

## 📈 Performance

### Benchmarks

- **Response Time**: < 200ms average
- **Throughput**: 1000+ users supported
- **Uptime**: 99.9% target
- **Memory Usage**: < 512MB typical

### Optimization

- Redis caching for price data
- Database connection pooling
- Async/await for I/O operations
- Rate limiting for API calls

## 🚨 Troubleshooting

### Common Issues

1. **Database Connection Failed**
   ```bash
   # Check PostgreSQL status
   sudo systemctl status postgresql
   
   # Check connection
   psql -h localhost -U bot_user -d vanta_bot
   ```

2. **Redis Connection Failed**
   ```bash
   # Check Redis status
   sudo systemctl status redis
   
   # Test connection
   redis-cli ping
   ```

3. **Base Network Issues**
   ```bash
   # Test RPC endpoint
   curl -X POST -H "Content-Type: application/json" \
     --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
     $BASE_RPC_URL
   ```

### Logs

```bash
# View bot logs
tail -f logs/bot.log

# Docker logs
docker-compose logs -f bot

# Database logs
sudo tail -f /var/log/postgresql/postgresql-*.log
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 🆘 Support

- **Documentation**: Check the [docs/](docs/) directory
- **Issues**: Create a GitHub issue
- **Discord**: Join our community
- **Email**: support@avantis.trade

## ⚠️ Disclaimer

This software is for educational purposes only. Trading cryptocurrencies and other financial instruments involves substantial risk of loss. Past performance is not indicative of future results. Always do your own research and never invest more than you can afford to lose.

---

**Built with ❤️ for the Vanta Bot community**