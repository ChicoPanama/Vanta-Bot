# 🔧 Vanta Bot - Configuration Guide

## 📋 **Step-by-Step Configuration**

### **Step 1: Environment Configuration**

1. **Copy environment template:**
   ```bash
   cp env.example .env
   ```

2. **Edit .env file with your values:**
   ```env
   # Telegram Bot (Required)
   TELEGRAM_BOT_TOKEN=1234567890:ABCdefGhIjKlmNoPQRsTuVwXyZ
   
   # Base Chain (Required)
   BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/your-api-key
   BASE_CHAIN_ID=8453
   
   # Database (Required)
   DATABASE_URL=postgresql://bot_user:your_password@localhost:5432/vanta_bot
   
   # Redis (Required)
   REDIS_URL=redis://localhost:6379
   
   # Security (Required)
   ENCRYPTION_KEY=your-32-byte-encryption-key-here
   
   # Avantis Protocol (Required - Update with real addresses)
   AVANTIS_TRADING_CONTRACT=0x... # Replace with actual Avantis contract
   AVANTIS_VAULT_CONTRACT=0x...   # Replace with actual Avantis contract
   USDC_CONTRACT=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
   
   # Development
   DEBUG=true
   LOG_LEVEL=INFO
   ```

### **Step 2: Get Required Credentials**

#### **A. Telegram Bot Token**
1. Message @BotFather on Telegram
2. Send `/newbot`
3. Choose name: `Vanta Bot`
4. Choose username: `your_bot_username_bot`
5. Copy the token to `TELEGRAM_BOT_TOKEN`

#### **B. Base Network RPC**
1. **Alchemy (Recommended):**
   - Go to [alchemy.com](https://www.alchemy.com/)
   - Create account and new app
   - Select "Base" network
   - Copy HTTP URL to `BASE_RPC_URL`

2. **QuickNode (Alternative):**
   - Go to [quicknode.com](https://www.quicknode.com/)
   - Create account and new endpoint
   - Select "Base" network
   - Copy HTTP URL to `BASE_RPC_URL`

#### **C. Database Setup**
1. **Install PostgreSQL:**
   ```bash
   # Ubuntu/Debian
   sudo apt install postgresql postgresql-contrib
   
   # macOS
   brew install postgresql
   
   # Windows
   # Download from postgresql.org
   ```

2. **Create Database:**
   ```sql
   sudo -u postgres psql
   CREATE DATABASE vanta_bot;
   CREATE USER bot_user WITH ENCRYPTED PASSWORD 'your_secure_password';
   GRANT ALL PRIVILEGES ON DATABASE vanta_bot TO bot_user;
   \q
   ```

3. **Update DATABASE_URL:**
   ```env
   DATABASE_URL=postgresql://bot_user:your_secure_password@localhost:5432/vanta_bot
   ```

#### **D. Redis Setup**
1. **Install Redis:**
   ```bash
   # Ubuntu/Debian
   sudo apt install redis-server
   
   # macOS
   brew install redis
   
   # Windows
   # Download from redis.io
   ```

2. **Start Redis:**
   ```bash
   # Linux
   sudo systemctl start redis
   
   # macOS
   brew services start redis
   ```

#### **E. Generate Encryption Key**
1. **Run key generator:**
   ```bash
   python3 generate_key.py
   ```

2. **Copy the generated key to ENCRYPTION_KEY in .env**

#### **F. Avantis Protocol Contracts**
1. **Get real contract addresses from Avantis Protocol**
2. **Update in .env:**
   ```env
   AVANTIS_TRADING_CONTRACT=0x... # Real Avantis trading contract
   AVANTIS_VAULT_CONTRACT=0x...   # Real Avantis vault contract
   ```

### **Step 3: Deploy Bot**

1. **Run deployment script:**
   ```bash
   ./deploy.sh
   ```

2. **If deployment fails, install dependencies manually:**
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Test bot structure:**
   ```bash
   python3 test_simple.py
   ```

### **Step 4: Start Bot**

1. **Start the bot:**
   ```bash
   python3 main.py
   ```

2. **Expected output:**
   ```
   2024-01-01 12:00:00,000 - __main__ - INFO - Starting Vanta Bot with Advanced Features...
   2024-01-01 12:00:01,000 - __main__ - INFO - Bot started successfully
   ```

3. **Test in Telegram:**
   - Find your bot by username
   - Send `/start` command
   - Choose Simple or Advanced interface
   - Test trading features

### **Step 5: Production Deployment**

#### **A. Docker Deployment**
1. **Build and start:**
   ```bash
   docker-compose up -d
   ```

2. **View logs:**
   ```bash
   docker-compose logs -f bot
   ```

#### **B. System Service**
1. **Copy service file:**
   ```bash
   sudo cp vanta-bot.service /etc/systemd/system/
   ```

2. **Enable and start:**
   ```bash
   sudo systemctl enable vanta-bot
   sudo systemctl start vanta-bot
   ```

3. **Check status:**
   ```bash
   sudo systemctl status vanta-bot
   ```

## 🧪 **Testing Checklist**

### **Basic Tests**
- [ ] Bot responds to `/start` command
- [ ] User type selection works (Simple/Advanced)
- [ ] Wallet creation works
- [ ] Navigation between interfaces works
- [ ] Quick trade interface works (Simple users)
- [ ] Advanced trading interface works (Advanced users)

### **Advanced Tests**
- [ ] Position management features work
- [ ] Risk management tools work
- [ ] Analytics and performance tracking work
- [ ] Market data integration works
- [ ] Alert system works
- [ ] Settings configuration works

### **Avantis Integration Tests**
- [ ] All features use Avantis SDK methods
- [ ] TP/SL management works with `build_trade_tp_sl_update_tx`
- [ ] Position updates work with `update_position_leverage`
- [ ] Risk calculations work with `get_portfolio_risk_metrics`
- [ ] Real-time data works with `get_real_time_prices`

## 🚨 **Troubleshooting**

### **Common Issues**

1. **"Module not found" errors:**
   ```bash
   pip3 install -r requirements.txt
   ```

2. **Database connection failed:**
   ```bash
   # Check PostgreSQL status
   sudo systemctl status postgresql
   
   # Test connection
   psql -h localhost -U bot_user -d vanta_bot
   ```

3. **Redis connection failed:**
   ```bash
   # Check Redis status
   sudo systemctl status redis
   
   # Test connection
   redis-cli ping
   ```

4. **Base network issues:**
   ```bash
   # Test RPC endpoint
   curl -X POST -H "Content-Type: application/json" \
     --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
     $BASE_RPC_URL
   ```

5. **Bot not responding:**
   ```bash
   # Check bot logs
   tail -f logs/bot.log
   
   # Check configuration
   python3 -c "from src.config.settings import config; print('Config loaded')"
   ```

## 📊 **Performance Monitoring**

### **Health Checks**
- Bot response time < 200ms
- Database connection stable
- Redis cache working
- Base network connectivity

### **Logs**
- Application logs: `logs/bot.log`
- Error logs: `logs/error.log`
- Access logs: `logs/access.log`

## 🎉 **Success Criteria**

Your bot is successfully deployed when:

- ✅ Bot responds to all commands
- ✅ User type selection works
- ✅ Simple and Advanced interfaces work
- ✅ All Avantis-compatible features work
- ✅ Database and Redis connections stable
- ✅ Real-time data integration works
- ✅ No critical errors in logs

## 🚀 **Next Steps After Deployment**

1. **Monitor Performance** - Check logs and metrics
2. **Test Trading** - Execute test trades (start small)
3. **User Feedback** - Gather feedback from beta users
4. **Optimize** - Improve performance based on usage
5. **Scale** - Add more features as needed

**Your Vanta Bot is now ready for production use! 🎉**
