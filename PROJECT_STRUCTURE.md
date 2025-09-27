# Vanta Bot - Project Structure

This document outlines the clean, organized structure of the Vanta Bot codebase.

## 📁 Directory Structure

```
vanta-bot/
├── 📁 src/                          # Source code
│   ├── 📁 ai/                       # AI/ML components
│   │   ├── __init__.py
│   │   ├── market_intelligence.py   # Market analysis AI
│   │   └── trader_analyzer.py       # Trader analysis ML models
│   │
│   ├── 📁 analytics/                # Analytics and tracking
│   │   ├── __init__.py
│   │   ├── data_extractor.py        # Data extraction utilities
│   │   └── position_tracker.py      # Position tracking
│   │
│   ├── 📁 blockchain/               # Blockchain integration
│   │   ├── __init__.py
│   │   ├── avantis_client.py        # Avantis protocol client
│   │   ├── avantis_sdk_integration.py # SDK integration
│   │   ├── base_client.py           # Base network client
│   │   └── wallet_manager.py        # Wallet management
│   │
│   ├── 📁 bot/                      # Telegram bot components
│   │   ├── __init__.py
│   │   ├── 📁 handlers/             # Bot command handlers
│   │   │   ├── __init__.py
│   │   │   ├── start.py             # /start and /help commands
│   │   │   ├── wallet.py            # Wallet management
│   │   │   ├── trading.py           # Trading operations
│   │   │   ├── positions.py         # Position management
│   │   │   ├── portfolio.py         # Portfolio overview
│   │   │   ├── orders.py            # Order management
│   │   │   ├── settings.py          # User settings
│   │   │   ├── user_types.py        # User interface types
│   │   │   ├── advanced_trading.py  # Advanced trading features
│   │   │   ├── ai_insights_handlers.py # AI insights
│   │   │   └── copytrading_handlers.py # Copy trading
│   │   │
│   │   ├── 📁 keyboards/            # Inline keyboards
│   │   │   ├── __init__.py
│   │   │   └── trading_keyboards.py # Trading UI keyboards
│   │   │
│   │   └── 📁 utils/                # Bot utilities
│   │       └── __init__.py
│   │
│   ├── 📁 config/                   # Configuration management
│   │   ├── __init__.py
│   │   └── settings.py              # Centralized configuration
│   │
│   ├── 📁 copy_trading/             # Copy trading system
│   │   ├── __init__.py
│   │   ├── copy_executor.py         # Copy execution engine
│   │   └── leaderboard_service.py   # Leaderboard management
│   │
│   ├── 📁 database/                 # Database layer
│   │   ├── __init__.py
│   │   ├── models.py                # SQLAlchemy models
│   │   └── operations.py            # Database operations
│   │
│   ├── 📁 middleware/               # Middleware components
│   │   ├── __init__.py
│   │   └── rate_limiter.py          # Rate limiting
│   │
│   ├── 📁 monitoring/               # Monitoring and metrics
│   │   ├── __init__.py
│   │   └── performance_monitor.py   # Performance monitoring
│   │
│   ├── 📁 services/                 # Business logic services
│   │   ├── __init__.py
│   │   ├── analytics.py             # Analytics service
│   │   ├── cache_service.py         # Caching service
│   │   ├── position_monitor.py      # Position monitoring
│   │   └── price_service.py         # Price data service
│   │
│   └── 📁 utils/                    # General utilities
│       ├── __init__.py
│       └── validators.py            # Input validation
│
├── 📁 tests/                        # Test suite
│   ├── 📁 copy_trading/             # Copy trading tests
│   │   ├── __init__.py
│   │   ├── test_ai_analyzer.py      # AI analyzer tests
│   │   ├── test_copy_executor.py    # Copy executor tests
│   │   ├── test_fifo_pnl.py         # FIFO PnL tests
│   │   ├── test_integration.py      # Integration tests
│   │   ├── test_leaderboard_service.py # Leaderboard tests
│   │   └── test_performance.py      # Performance tests
│   │
│   ├── test_basic.py                # Basic functionality tests
│   ├── test_compatibility.py        # Compatibility tests
│   ├── test_final_verification.py   # Final verification tests
│   ├── test_integration.py          # Integration tests
│   ├── test_main.py                 # Main application tests
│   ├── verify_setup.py              # Setup verification
│   └── README.md                    # Test documentation
│
├── 📁 docs/                         # Documentation
│   ├── compatibility.md             # Compatibility guide
│   ├── completion.md                # Completion status
│   ├── configuration.md             # Configuration guide
│   ├── README.md                    # Documentation overview
│   ├── setup-complete.md            # Setup completion guide
│   ├── setup.md                     # Setup instructions
│   └── steps.md                     # Implementation steps
│
├── 📁 config/                       # Configuration files
│   ├── copy_trading_schema.sql      # Copy trading schema
│   ├── init.sql                     # Database initialization
│   └── vanta-bot.service            # Systemd service file
│
├── 📁 scripts/                      # Utility scripts
│   ├── deploy.sh                    # Deployment script
│   ├── generate_key.py              # Key generation
│   ├── setup.py                     # Setup script
│   └── README.md                    # Scripts documentation
│
├── 📁 logs/                         # Application logs
├── 📁 data/                         # Data storage
│
├── main.py                          # Application entry point
├── requirements.txt                 # Python dependencies
├── Dockerfile                       # Docker configuration
├── docker-compose.yml               # Docker Compose setup
├── env.example                      # Environment template
├── .gitignore                       # Git ignore rules
├── LICENSE                          # License file
├── README.md                        # Project overview
├── PROJECT_STRUCTURE.md             # This file
└── COPY_TRADING_IMPLEMENTATION.md   # Copy trading docs
```

## 🏗️ Architecture Overview

### Core Components

1. **Main Application** (`main.py`)
   - Entry point for the Telegram bot
   - Application factory and configuration
   - Handler registration and routing

2. **Configuration** (`src/config/`)
   - Centralized configuration management
   - Environment variable handling
   - Validation and defaults

3. **Bot Handlers** (`src/bot/handlers/`)
   - Modular command handlers
   - User interface management
   - Trading operations

4. **Blockchain Integration** (`src/blockchain/`)
   - Avantis protocol integration
   - Base network connectivity
   - Wallet management

5. **Database Layer** (`src/database/`)
   - SQLAlchemy models
   - Database operations
   - Connection management

6. **AI/ML Components** (`src/ai/`)
   - Market intelligence
   - Trader analysis
   - Machine learning models

7. **Copy Trading** (`src/copy_trading/`)
   - Copy execution engine
   - Leaderboard service
   - Performance tracking

8. **Monitoring** (`src/monitoring/`)
   - Performance monitoring
   - Health checks
   - Metrics collection

## 📋 Design Principles

### 1. Modularity
- Each component has a single responsibility
- Clear separation of concerns
- Easy to test and maintain

### 2. Configuration Management
- Environment-based configuration
- Centralized settings
- Validation and defaults

### 3. Error Handling
- Comprehensive error handling
- Logging and monitoring
- Graceful degradation

### 4. Testing
- Comprehensive test coverage
- Unit and integration tests
- Performance testing

### 5. Documentation
- Clear code documentation
- API documentation
- Setup and deployment guides

## 🔧 Development Guidelines

### File Naming
- Use snake_case for Python files
- Use descriptive names
- Group related functionality

### Import Organization
```python
# Standard library imports
import logging
from typing import Optional

# Third-party imports
from telegram import Update
from sqlalchemy import create_engine

# Local imports
from ..config.settings import config
from .models import User
```

### Code Structure
```python
"""
Module documentation
Brief description of the module's purpose
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ExampleClass:
    """Class documentation"""
    
    def __init__(self):
        """Initialize the class"""
        pass
    
    def example_method(self) -> Optional[str]:
        """Method documentation"""
        return None
```

## 🚀 Getting Started

1. **Clone the repository**
2. **Copy environment template**: `cp env.example .env`
3. **Configure environment variables** in `.env`
4. **Install dependencies**: `pip install -r requirements.txt`
5. **Run the application**: `python main.py`

## 📚 Additional Resources

- [README.md](README.md) - Project overview and features
- [docs/](docs/) - Detailed documentation
- [tests/](tests/) - Test suite and examples
- [COPY_TRADING_IMPLEMENTATION.md](COPY_TRADING_IMPLEMENTATION.md) - Copy trading implementation

---

This structure provides a clean, maintainable, and scalable foundation for the Vanta Bot project.
