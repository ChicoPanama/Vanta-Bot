#!/usr/bin/env python3
"""
Vanta Bot Setup Script
This script helps you set up the bot environment and configuration.
"""

import secrets
import subprocess
import sys
from pathlib import Path


def print_banner():
    """Print setup banner"""
    print(
        """
╔══════════════════════════════════════════════════════════════╗
║                Vanta Bot Setup                    ║
║                                                              ║
║  🚀 Complete Telegram Trading Bot for Avantis Protocol      ║
║  📊 80+ Markets | 500x Leverage | Zero Fees               ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """
    )


def check_python_version():
    """Check if Python version is compatible"""
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True


def install_dependencies():
    """Install required dependencies"""
    print("\n📦 Installing dependencies...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
        )
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False


def generate_encryption_key():
    """Generate a secure encryption key"""
    return secrets.token_urlsafe(32)


def create_env_file():
    """Create .env file with template values"""
    env_path = Path(".env")

    if env_path.exists():
        print("⚠️  .env file already exists. Skipping creation.")
        return True

    print("\n🔧 Creating .env file...")

    # Generate encryption key
    encryption_key = generate_encryption_key()

    env_content = f"""# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Base Chain Configuration
BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/your-api-key
BASE_CHAIN_ID=8453

# Database Configuration
DATABASE_URL=postgresql://bot_user:your_secure_password@localhost:5432/vanta_bot

# Redis Configuration
REDIS_URL=redis://localhost:6379

# Security
ENCRYPTION_KEY={encryption_key}

# Avantis Protocol Contracts (Base mainnet)
AVANTIS_TRADING_CONTRACT=0x... # Replace with actual contract address
AVANTIS_VAULT_CONTRACT=0x...   # Replace with actual contract address
USDC_CONTRACT=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913

# Development Settings
DEBUG=true
LOG_LEVEL=INFO

# Optional: Monitoring
GRAFANA_PASSWORD=admin123
POSTGRES_PASSWORD=secure_password_here
"""

    with open(env_path, "w") as f:
        f.write(env_content)

    print("✅ .env file created")
    print(f"🔑 Generated encryption key: {encryption_key}")
    return True


def create_directories():
    """Create necessary directories"""
    print("\n📁 Creating directories...")
    directories = ["logs", "data", "monitoring"]

    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"   ✅ Created {directory}/")

    return True


def create_init_sql():
    """Create database initialization script"""
    init_sql_path = Path("init.sql")

    if init_sql_path.exists():
        return True

    print("\n🗄️  Creating database initialization script...")

    init_sql_content = """-- Database initialization for Vanta Bot
-- This script sets up the database with proper permissions

-- Create database if it doesn't exist
SELECT 'CREATE DATABASE vanta_bot'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'vanta_bot')\\gexec

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE vanta_bot TO bot_user;
"""

    with open(init_sql_path, "w") as f:
        f.write(init_sql_content)

    print("✅ Database initialization script created")
    return True


def create_monitoring_config():
    """Create monitoring configuration"""
    monitoring_dir = Path("monitoring")
    monitoring_dir.mkdir(exist_ok=True)

    prometheus_config = """global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'vanta-bot'
    static_configs:
      - targets: ['bot:8000']
"""

    prometheus_path = monitoring_dir / "prometheus.yml"
    with open(prometheus_path, "w") as f:
        f.write(prometheus_config)

    print("✅ Monitoring configuration created")
    return True


def print_next_steps():
    """Print next steps for the user"""
    print(
        """
🎉 Setup completed successfully!

📋 Next Steps:

1. 🔧 Configure your .env file:
   - Set your TELEGRAM_BOT_TOKEN from @BotFather
   - Set your BASE_RPC_URL (Alchemy/QuickNode)
   - Update contract addresses with real Avantis addresses

2. 🗄️  Set up database:
   # Install PostgreSQL
   sudo apt install postgresql postgresql-contrib  # Ubuntu/Debian
   brew install postgresql                          # macOS

   # Create database
   sudo -u postgres psql
   CREATE DATABASE vanta_bot;
   CREATE USER bot_user WITH ENCRYPTED PASSWORD 'your_secure_password';
   GRANT ALL PRIVILEGES ON DATABASE vanta_bot TO bot_user;

3. 🔴 Set up Redis:
   sudo apt install redis-server  # Ubuntu/Debian
   brew install redis              # macOS
   sudo systemctl start redis      # Linux
   brew services start redis       # macOS

4. 🧪 Test the bot:
   python test_bot.py

5. 🚀 Start the bot:
   python main.py

6. 🐳 Or use Docker:
   docker-compose up -d

📚 Documentation:
- Bot Commands: /start, /help, /wallet, /trade, /positions
- Trading: 80+ markets, up to 500x leverage
- Security: Encrypted private keys, rate limiting
- Features: Real-time prices, position monitoring

🆘 Need help? Check the README.md or contact support.
    """
    )


def main():
    """Main setup function"""
    print_banner()

    # Check Python version
    if not check_python_version():
        sys.exit(1)

    # Install dependencies
    if not install_dependencies():
        print("❌ Setup failed at dependency installation")
        sys.exit(1)

    # Create .env file
    if not create_env_file():
        print("❌ Setup failed at .env creation")
        sys.exit(1)

    # Create directories
    if not create_directories():
        print("❌ Setup failed at directory creation")
        sys.exit(1)

    # Create database init script
    if not create_init_sql():
        print("❌ Setup failed at database script creation")
        sys.exit(1)

    # Create monitoring config
    if not create_monitoring_config():
        print("❌ Setup failed at monitoring config creation")
        sys.exit(1)

    print_next_steps()


if __name__ == "__main__":
    main()
