# 🚀 Complete Setup Guide: Vanta Bot

This guide will walk you through setting up the complete Vanta Bot from scratch.

## 📋 Prerequisites Checklist

Before starting, ensure you have:

- [ ] Python 3.9+ installed
- [ ] PostgreSQL 12+ installed
- [ ] Redis 6+ installed
- [ ] Telegram account
- [ ] Base network RPC access (Alchemy/QuickNode)
- [ ] Code editor (VS Code recommended)

## 🎯 Step 1: Create Telegram Bot

### 1.1 Get Bot Token

1. Open Telegram and search for `@BotFather`
2. Start a chat and send `/start`
3. Send `/newbot`
4. Choose a name: `Vanta Bot`
5. Choose a username: `your_bot_username_bot`
6. **Save the API token** - you'll get something like: `1234567890:ABCdefGhIjKlmNoPQRsTuVwXyZ`

### 1.2 Set Bot Commands

Send this to @BotFather:

```
/setcommands
```

Select your bot and paste:

```
start - 🚀 Start trading with Avantis
wallet - 💰 View wallet and balance
trade - 📊 Open trading interface
positions - 📈 View open positions
orders - 📋 Pending orders
portfolio - 🏦 Portfolio analytics
settings - ⚙️ Bot settings
help - ❓ Get help
```

## 🗄️ Step 2: Set Up Database

### 2.1 Install PostgreSQL

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**macOS:**
```bash
brew install postgresql
brew services start postgresql
```

**Windows:**
Download from [postgresql.org](https://www.postgresql.org/download/windows/)

### 2.2 Create Database

```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Create database and user
CREATE DATABASE vanta_bot;
CREATE USER bot_user WITH ENCRYPTED PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE vanta_bot TO bot_user;
\q
```

## 🔴 Step 3: Set Up Redis

### 3.1 Install Redis

**Ubuntu/Debian:**
```bash
sudo apt install redis-server
sudo systemctl start redis
sudo systemctl enable redis
```

**macOS:**
```bash
brew install redis
brew services start redis
```

**Windows:**
Download from [redis.io](https://redis.io/download)

### 3.2 Test Redis

```bash
redis-cli ping
# Should return: PONG
```

## 🌐 Step 4: Get Base Network Access

### 4.1 Choose RPC Provider

**Option A: Alchemy (Recommended)**
1. Go to [alchemy.com](https://www.alchemy.com/)
2. Create account and new app
3. Select "Base" network
4. Copy the HTTP URL

**Option B: QuickNode**
1. Go to [quicknode.com](https://www.quicknode.com/)
2. Create account and new endpoint
3. Select "Base" network
4. Copy the HTTP URL

### 4.2 Test Connection

```bash
curl -X POST -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
  YOUR_BASE_RPC_URL
```

## 🚀 Step 5: Set Up Bot Project

### 5.1 Clone and Install

```bash
# Clone repository
git clone <repository-url>
cd vanta-bot

# Create virtual environment
python -m venv avantis_env

# Activate virtual environment
# On Windows:
avantis_env\Scripts\activate
# On macOS/Linux:
source avantis_env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 5.2 Run Setup Script

```bash
python setup.py
```

This will:
- Create `.env` file with template values
- Generate encryption key
- Create necessary directories
- Set up monitoring configuration

### 5.3 Configure Environment

Edit `.env` file with your actual values:

```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGhIjKlmNoPQRsTuVwXyZ

# Base Chain
BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/your-api-key
BASE_CHAIN_ID=8453

# Database
DATABASE_URL=postgresql://bot_user:your_secure_password@localhost:5432/vanta_bot

# Redis
REDIS_URL=redis://localhost:6379

# Security
ENCRYPTION_KEY=your-generated-32-byte-key

# Avantis Protocol (Update with real addresses)
AVANTIS_TRADING_CONTRACT=0x... # Replace with actual contract
AVANTIS_VAULT_CONTRACT=0x...   # Replace with actual contract
USDC_CONTRACT=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913

# Development
DEBUG=true
LOG_LEVEL=INFO
```

## 🧪 Step 6: Test Installation

### 6.1 Run Test Suite

```bash
python test_bot.py
```

Expected output:
```
🧪 Testing Vanta Bot Components...
==================================================
1. Testing database connection...
   ✅ Database connected and tables created
2. Testing wallet creation...
   ✅ Wallet created: 0x...
3. Testing Base network connection...
   ✅ Base network connected
4. Testing configuration...
   ✅ All required configurations present
5. Testing wallet balance retrieval...
   ✅ ETH Balance: 0.000000 ETH
   ✅ USDC Balance: 0.00 USDC
6. Testing database operations...
   ✅ User creation successful
   ✅ Position creation successful

🎉 All tests passed! Bot is ready to run.
```

### 6.2 Fix Any Issues

If tests fail, check:

1. **Database Connection**: Ensure PostgreSQL is running and credentials are correct
2. **Redis Connection**: Ensure Redis is running
3. **Base RPC**: Test your RPC endpoint manually
4. **Dependencies**: Ensure all packages are installed

## 🚀 Step 7: Start the Bot

### 7.1 Start Bot

```bash
python main.py
```

Expected output:
```
2024-01-01 12:00:00,000 - __main__ - INFO - Starting Vanta Bot...
2024-01-01 12:00:01,000 - __main__ - INFO - Bot started successfully
```

### 7.2 Test in Telegram

1. Find your bot by username
2. Send `/start` command
3. Verify wallet creation
4. Test navigation buttons

## 🐳 Step 8: Docker Deployment (Optional)

### 8.1 Using Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f bot

# Stop services
docker-compose down
```

### 8.2 Manual Docker

```bash
# Build image
docker build -t vanta-bot .

# Run container
docker run -d --name vanta-bot \
  --env-file .env \
  vanta-bot
```

## 📊 Step 9: Monitoring Setup

### 9.1 Enable Monitoring (Optional)

```bash
# Start with monitoring
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d
```

### 9.2 Access Dashboards

- **Grafana**: http://localhost:3000 (admin/admin123)
- **Prometheus**: http://localhost:9090

## 🔧 Step 10: Production Configuration

### 10.1 Security Hardening

1. **Change Default Passwords**
2. **Enable SSL/TLS**
3. **Set up Firewall Rules**
4. **Configure Backup Strategy**

### 10.2 Performance Optimization

1. **Database Tuning**
2. **Redis Configuration**
3. **Load Balancing**
4. **Caching Strategy**

## 🚨 Troubleshooting

### Common Issues

#### Database Connection Failed
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Check connection
psql -h localhost -U bot_user -d vanta_bot

# Reset password if needed
sudo -u postgres psql
ALTER USER bot_user PASSWORD 'new_password';
```

#### Redis Connection Failed
```bash
# Check Redis status
sudo systemctl status redis

# Test connection
redis-cli ping

# Check configuration
redis-cli config get bind
```

#### Base Network Issues
```bash
# Test RPC endpoint
curl -X POST -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
  $BASE_RPC_URL

# Check network status
curl -X POST -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","method":"net_version","params":[],"id":1}' \
  $BASE_RPC_URL
```

#### Bot Not Responding
```bash
# Check bot logs
tail -f logs/bot.log

# Check database connection
python -c "from src.database.operations import db; print(db.get_session())"

# Test individual components
python -c "from src.blockchain.base_client import base_client; print(base_client.w3.is_connected())"
```

### Performance Issues

#### High Memory Usage
```bash
# Check memory usage
htop

# Optimize database
VACUUM ANALYZE;

# Clear Redis cache
redis-cli FLUSHALL
```

#### Slow Response Times
```bash
# Check database performance
EXPLAIN ANALYZE SELECT * FROM users;

# Monitor Redis
redis-cli MONITOR

# Check network latency
ping your-rpc-provider.com
```

## 📈 Step 11: Advanced Configuration

### 11.1 Custom Trading Pairs

Edit `src/bot/keyboards/trading_keyboards.py`:

```python
def get_crypto_assets_keyboard():
    keyboard = [
        [InlineKeyboardButton("₿ BTC", callback_data="asset_BTC"),
         InlineKeyboardButton("⟠ ETH", callback_data="asset_ETH")],
        [InlineKeyboardButton("◎ SOL", callback_data="asset_SOL"),
         InlineKeyboardButton("🔺 AVAX", callback_data="asset_AVAX")],
        # Add more assets here
        [InlineKeyboardButton("🔙 Back", callback_data="trade")]
    ]
    return InlineKeyboardMarkup(keyboard)
```

### 11.2 Custom Risk Management

Edit `src/config/settings.py`:

```python
class Config:
    # Trading limits
    MAX_LEVERAGE = 500
    MIN_POSITION_SIZE = 1  # USDC
    MAX_POSITION_SIZE = 100000  # USDC
    
    # Risk management
    LIQUIDATION_THRESHOLD = 0.95  # 95% loss
    MAX_DAILY_LOSS = 1000  # USDC
    MAX_OPEN_POSITIONS = 10
```

### 11.3 Custom Notifications

Edit `src/services/position_monitor.py`:

```python
async def send_custom_alert(self, user_id: int, message: str):
    """Send custom alert to user"""
    try:
        await self.bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error sending alert: {e}")
```

## 🎉 Congratulations!

You now have a fully functional Vanta Bot! 

### What You've Built:

✅ **Complete Trading Bot** with 80+ markets and 500x leverage  
✅ **Secure Wallet Management** with encrypted private keys  
✅ **Real-time Position Monitoring** with liquidation alerts  
✅ **Portfolio Analytics** with performance tracking  
✅ **Production-ready Deployment** with Docker support  
✅ **Comprehensive Monitoring** with Grafana dashboards  

### Next Steps:

1. **Get Real Contract Addresses** from Avantis Protocol
2. **Test on Base Testnet** before mainnet
3. **Set Up Monitoring** for production
4. **Configure Backup Strategy** for data safety
5. **Add Custom Features** as needed

### Support:

- 📚 **Documentation**: Check README.md
- 🐛 **Issues**: Create GitHub issue
- 💬 **Community**: Join Discord
- 📧 **Email**: support@avantis.trade

---

**Happy Trading! 🚀📈**