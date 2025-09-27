# Copy Trading System - Troubleshooting Guide

## Quick Start Checklist

1. **Environment Variables**
   ```bash
   export BASE_RPC_URL=https://mainnet.base.org
   export BASE_WS_URL=wss://mainnet.base.org  # Optional
   export AVANTIS_TRADING_CONTRACT=0x...  # Your Avantis trading contract
   export AVANTIS_VAULT_CONTRACT=0x...    # Optional
   export DATABASE_URL=sqlite:///vanta_bot.db
   ```

2. **ABI Files**
   - Ensure `config/abis/Trading.json` exists
   - Ensure `config/abis/Vault.json` exists

3. **Database Migration**
   ```bash
   alembic upgrade head
   ```

## Common Issues & Solutions

### 1. Alembic Version Drift

**Problem**: `alembic_version` table is empty but tables exist

**Solution**:
```bash
alembic stamp head
```

### 2. Empty Leaderboard

**Problem**: `/alfa top50` returns "No leaders yet"

**Solutions**:
1. **Check if indexer is running**:
   ```bash
   python3 -m src.services.indexers.run_indexer
   ```

2. **Lower thresholds temporarily**:
   ```bash
   export LEADER_MIN_TRADES_30D=10
   export LEADER_MIN_VOLUME_30D_USD=100000
   ```

3. **Check database for data**:
   ```sql
   SELECT COUNT(*) FROM fills;
   SELECT MIN(ts), MAX(ts) FROM fills;
   ```

### 3. SQLite vs Postgres Math

**Problem**: Complex SQL functions don't work in SQLite

**Solution**: The system uses simplified queries compatible with SQLite:
- `AVG()` instead of `PERCENTILE_CONT()`
- `strftime()` instead of `extract(epoch from now())`

### 4. WebSocket Connection Issues

**Problem**: Indexer fails to connect or loses connection

**Solutions**:
1. **Check RPC URLs**:
   ```bash
   curl -X POST -H "Content-Type: application/json" \
        --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
        $BASE_RPC_URL
   ```

2. **Reduce backfill step size**:
   ```python
   # In run_indexer.py, change:
   from_block = max(0, latest - 10_000)  # Smaller range
   ```

3. **Add delays between requests**:
   ```python
   await asyncio.sleep(0.25)  # Add after each batch
   ```

### 5. Database Connection Issues

**Problem**: Database connection fails

**Solutions**:
1. **Check DATABASE_URL**:
   ```bash
   echo $DATABASE_URL
   ```

2. **Test connection**:
   ```bash
   sqlite3 vanta_bot.db ".tables"
   ```

3. **Check permissions**:
   ```bash
   ls -la vanta_bot.db
   ```

### 6. Clean PnL Not Calculating

**Problem**: Clean PnL shows as 0 or null

**Solutions**:
1. **Check fills data**:
   ```sql
   SELECT address, side, is_long, size, price, fee 
   FROM fills 
   WHERE address = '0x...' 
   ORDER BY ts;
   ```

2. **Test FIFO calculation**:
   ```bash
   python3 -m pytest tests/test_pnl_fifo.py -v
   ```

### 7. Bot Not Starting

**Problem**: Telegram bot fails to start

**Solutions**:
1. **Check bot token**:
   ```bash
   echo $TELEGRAM_BOT_TOKEN
   ```

2. **Check imports**:
   ```bash
   python3 -c "from src.bot.handlers.alfa_handlers import alfa_handlers; print('OK')"
   ```

3. **Check background services**:
   ```bash
   python3 -c "from main import start_background_services; print('OK')"
   ```

## Sanity Check Commands

Run these to verify system health:

```bash
# Full system check
python3 scripts/sanity_checks.py

# Test FIFO PnL calculation
python3 -m pytest tests/test_pnl_fifo.py -v

# Check database
sqlite3 vanta_bot.db ".tables"
sqlite3 vanta_bot.db "SELECT COUNT(*) FROM fills;"

# Test leaderboard service
python3 -c "
import asyncio
from src.services.analytics.leaderboard_service import LeaderboardService
from sqlalchemy import create_engine

async def test():
    engine = create_engine('sqlite:///vanta_bot.db')
    lb = LeaderboardService(engine)
    traders = await lb.top_traders(5)
    print(f'Found {len(traders)} traders')

asyncio.run(test())
"
```

## Performance Tuning

### For High-Volume Environments

1. **Increase batch sizes**:
   ```python
   # In avantis_indexer.py
   BATCH_SIZE = 1000  # Increase from 100
   ```

2. **Add connection pooling**:
   ```python
   engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20)
   ```

3. **Use PostgreSQL**:
   ```bash
   export DATABASE_URL=postgresql://user:pass@localhost/db
   ```

### For Development

1. **Reduce backfill range**:
   ```python
   backfill_from = max(0, latest - 1_000)  # Last 1k blocks
   ```

2. **Increase logging**:
   ```python
   logging.getLogger().setLevel(logging.DEBUG)
   ```

## Monitoring

### Key Metrics to Watch

1. **Indexer Health**:
   - Blocks processed per minute
   - Events processed per minute
   - Database write latency

2. **Leaderboard Health**:
   - Number of qualified traders
   - Clean PnL calculation time
   - Cache hit rate (if using Redis)

3. **Bot Health**:
   - Telegram API response time
   - Command execution time
   - Background task status

### Log Patterns to Monitor

```bash
# Indexer progress
grep "Persisted fill" logs/app.log | tail -10

# Leaderboard updates
grep "Computed leaderboard" logs/app.log

# Error patterns
grep "ERROR\|Exception" logs/app.log | tail -20
```

## Getting Help

1. **Check logs**:
   ```bash
   tail -f logs/app.log
   ```

2. **Run sanity checks**:
   ```bash
   python3 scripts/sanity_checks.py
   ```

3. **Test individual components**:
   ```bash
   python3 -m src.services.indexers.abi_inspector
   python3 -m pytest tests/ -v
   ```

4. **Verify environment**:
   ```bash
   env | grep -E "(BASE_|AVANTIS_|DATABASE_|TELEGRAM_)"
   ```
