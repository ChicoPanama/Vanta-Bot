# Copy Trading Features Documentation

## Overview

Vanta Bot now includes comprehensive AI-powered copy trading functionality that allows users to automatically copy trades from successful Avantis Protocol traders. The system combines real-time blockchain event monitoring, AI-powered trader analysis, market intelligence, and automated trade execution.

## Architecture

### Core Components

1. **Event Indexer** (`src/analytics/data_extractor.py`)
   - Monitors Base chain for Avantis Trading contract events
   - Backfills historical data and provides real-time updates
   - Handles `TradeOpened` and `TradeClosed` events

2. **Position Tracker** (`src/analytics/position_tracker.py`)
   - Tracks trader positions in real-time
   - Calculates FIFO PnL for accurate performance measurement
   - Maintains trader statistics and metrics

3. **AI Trader Analyzer** (`src/ai/trader_analyzer.py`)
   - Uses ML models to analyze trader performance
   - Classifies traders into archetypes (Conservative Scalper, Risk Manager, etc.)
   - Provides risk assessment and copyability scores

4. **Market Intelligence** (`src/ai/market_intelligence.py`)
   - Monitors price feeds via Pyth Network
   - Classifies market regimes (Green/Yellow/Red)
   - Provides copy timing signals

5. **Copy Executor** (`src/copy_trading/copy_executor.py`)
   - Handles copy trade execution with slippage protection
   - Manages user copytrader profiles and configurations
   - Implements rate limiting and safety checks

6. **Leaderboard Service** (`src/copy_trading/leaderboard_service.py`)
   - Ranks traders using AI-powered algorithms
   - Provides detailed trader profiles and analysis
   - Handles search and filtering functionality

## Database Schema

### New Tables

#### `trader_stats`
Stores aggregated trader performance statistics with FIFO PnL calculation.

#### `copytrader_profiles`
User copytrader profiles with individual settings and configurations.

#### `copy_configurations`
Detailed copy trading configuration per profile including sizing, risk limits, and filters.

#### `leader_follows`
Relationships between copytraders and leaders they follow.

#### `copy_positions`
Individual copy trades executed by the system with status tracking.

#### `trader_analytics`
AI-generated trader analysis and classification data.

#### `trade_events`
Raw blockchain events from Avantis Trading contract.

#### `performance_metrics`
System performance and operational metrics.

#### `health_checks`
Service health status monitoring.

## Telegram Bot Commands

### Copy Trading Commands

- `/copytrader` - Main copytrader management interface
- `/alfa` - View AI-powered trader leaderboard
- `/status` - Check copy trading status and performance
- `/alpha` - AI insights and market intelligence
- `/insights` - Quick market insights

### User Flow

1. **Setup Copytrader**
   - Create copytrader profile with name
   - Choose sizing method (Fixed Amount or Percentage)
   - Configure risk limits and filters

2. **Find Leaders**
   - Browse AI-ranked leaderboard
   - Analyze trader profiles and performance
   - Review AI insights and recommendations

3. **Follow Traders**
   - Select traders to follow
   - Configure copy settings
   - Monitor performance

4. **Manage Portfolio**
   - View copy trading status
   - Track performance attribution
   - Adjust settings as needed

## AI Features

### Trader Analysis

The AI system analyzes traders using multiple ML models:

- **Performance Prediction**: Random Forest model predicts future performance
- **Anomaly Detection**: Isolation Forest identifies unusual trading patterns
- **Archetype Classification**: K-Means clustering classifies trader types
- **Risk Assessment**: Comprehensive risk metrics including Sharpe-like ratio and drawdown

### Market Intelligence

Real-time market regime detection:

- **Green Regime**: Low volatility, favorable for copying
- **Yellow Regime**: Moderate volatility, copy with caution
- **Red Regime**: High volatility, avoid copying

### Copyability Scoring

Traders receive a 0-100 copyability score based on:
- Volume and liquidity
- Consistency and win rate
- Risk profile
- Archetype classification
- Recent activity

## Safety Features

### Risk Management

- **Slippage Protection**: Configurable maximum slippage limits
- **Leverage Limits**: Maximum leverage restrictions
- **Position Size Limits**: Notional caps and percentage limits
- **Pair Filtering**: Allow/block specific trading pairs

### Rate Limiting

- Maximum 10 copy trades per hour per pair
- User-specific rate limits
- System-wide safety thresholds

### Market Regime Filtering

- Automatic pause during high volatility
- Regime-based copy recommendations
- Real-time market condition monitoring

## Configuration

### Environment Variables

```bash
# Copy Trading Configuration
LEADER_ACTIVE_HOURS=72
LEADER_MIN_TRADES_30D=300
LEADER_MIN_VOLUME_30D_USD=10000000
PYTH_PRICE_FEED_IDS_JSON='{"BTC-USD":"...","ETH-USD":"...","SOL-USD":"...","AVAX-USD":"..."}'
AI_MODEL_UPDATE_INTERVAL=3600
COPY_EXECUTION_MAX_DELAY_MS=500

# Base Chain Event Monitoring
BASE_WS_URL=wss://base-mainnet.g.alchemy.com/v2/your-api-key
EVENT_BACKFILL_BLOCKS=1000
EVENT_MONITORING_INTERVAL=5
```

### Database Setup

Run the copy trading schema migration:

```sql
-- Apply the copy trading schema
\i config/copy_trading_schema.sql
```

## Deployment

### Docker Compose

The system includes optimized Docker configuration:

```yaml
services:
  bot:
    # Main bot service with copy trading
    volumes:
      - ./models:/app/models  # AI model storage
  
  ai-processor:
    # Optional: Separate AI processing service
    command: python -m src.ai.processor
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
```

### Production Considerations

1. **Resource Requirements**
   - Minimum 2GB RAM for AI processing
   - SSD storage for model files
   - Stable internet for blockchain connectivity

2. **Monitoring**
   - Health checks for all services
   - Performance metrics collection
   - Alert system for failures

3. **Security**
   - Secure private key management
   - Database encryption
   - Rate limiting and DDoS protection

## Testing

### Test Suite

Comprehensive test coverage:

- `tests/copy_trading/test_copy_executor.py` - Copy execution tests
- `tests/copy_trading/test_leaderboard_service.py` - Leaderboard functionality
- `tests/copy_trading/test_integration.py` - End-to-end integration tests

### Running Tests

```bash
# Run all copy trading tests
pytest tests/copy_trading/ -v

# Run specific test file
pytest tests/copy_trading/test_copy_executor.py -v

# Run with coverage
pytest tests/copy_trading/ --cov=src.copy_trading --cov-report=html
```

## Performance Monitoring

### Metrics Collected

- Copy trade execution rates
- AI analysis performance
- Market regime changes
- System health status
- Database and Redis metrics

### Health Checks

- Database connectivity and performance
- Redis connectivity and memory usage
- Blockchain connectivity
- Copy trading service status
- AI services status

## Troubleshooting

### Common Issues

1. **Copy Trades Not Executing**
   - Check market regime (may be in Red regime)
   - Verify slippage limits
   - Check leader activity

2. **AI Analysis Not Updating**
   - Verify model training status
   - Check data availability
   - Review error logs

3. **Database Connection Issues**
   - Check PostgreSQL status
   - Verify connection strings
   - Review connection pool settings

### Logs

Monitor logs for debugging:

```bash
# View bot logs
docker logs vanta-bot-bot-1

# View AI processor logs
docker logs vanta-bot-ai-processor-1

# View database logs
docker logs vanta-bot-postgres-1
```

## Future Enhancements

### Planned Features

1. **Advanced AI Models**
   - Deep learning models for trader analysis
   - Reinforcement learning for copy optimization
   - Sentiment analysis integration

2. **Enhanced Risk Management**
   - Dynamic position sizing
   - Portfolio-level risk controls
   - Advanced stop-loss mechanisms

3. **Social Features**
   - Trader following networks
   - Performance sharing
   - Community leaderboards

4. **Mobile Support**
   - Mobile-optimized interface
   - Push notifications
   - Offline mode

## Support

For technical support or feature requests:

- GitHub Issues: [Vanta Bot Repository](https://github.com/ChicoPanama/Vanta-Bot)
- Documentation: [Full Documentation](./README.md)
- Community: [Discord/Telegram Community]

## Disclaimer

Copy trading involves significant financial risk. Users should:

- Only invest what they can afford to lose
- Understand the risks of automated trading
- Monitor their positions regularly
- Seek professional financial advice if needed

The Vanta Bot is provided for educational and informational purposes only and does not constitute financial advice.
