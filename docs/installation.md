# Installation Guide

Complete installation guide for Vanta Bot.

## Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (optional)

## Quick Installation

### Using Docker (Recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd avantis-telegram-bot
   ```

2. **Configure environment**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

3. **Start services**
   ```bash
   docker-compose up -d
   ```

### Manual Installation

1. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup database**
   ```bash
   # Create PostgreSQL database
   createdb vanta_bot
   
   # Run migrations
   alembic upgrade head
   ```

3. **Configure Redis**
   ```bash
   # Start Redis server
   redis-server
   ```

4. **Run the bot**
   ```bash
   python main.py
   ```

## Configuration

See [Configuration Guide](configuration.md) for detailed setup instructions.

## Verification

1. **Check bot status**
   ```bash
   curl http://localhost:8080/healthz
   ```

2. **Test Telegram bot**
   - Send `/start` to your bot
   - Verify wallet creation
   - Test basic commands

## Next Steps

- [Configure your bot](configuration.md)
- [Deploy to production](deployment.md)
- [Set up monitoring](monitoring.md)
