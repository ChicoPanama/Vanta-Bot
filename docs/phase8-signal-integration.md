# Phase 8: Signal Integration Guide

## Connecting Real Trading Signals

This guide shows how to integrate your existing indexer/tracker with the Phase 8 copy-trading system.

### **1. Basic Signal Integration**

In your indexer/tracker callback where you detect trader open/close events:

```python
from src.services.copytrading.alerts import on_trader_signal
from src.services.copytrading.copy_store import list_follows

async def on_trader_trade_detected(trader_key: str, trade_data: dict):
    """
    Called when a tracked trader opens or closes a position
    """
    # Get all users following this trader
    # Note: This is O(n) - consider adding reverse index for large scale
    all_follows = []
    # You'll need to iterate through all users or maintain a reverse index
    
    # For now, let's assume you have a way to get following users
    following_users = await get_users_following_trader(trader_key)
    
    # Send signals to all following users
    for user_id in following_users:
        signal = {
            "pair": trade_data["pair"],
            "side": "LONG" if trade_data["is_long"] else "SHORT",
            "lev": trade_data["leverage"],
            "notional_usd": trade_data["notional_usd"],
            "collateral_usdc": trade_data["collateral_usdc"]
        }
        
        await on_trader_signal(application.bot, user_id, trader_key, signal)
```

### **2. Optimized Reverse Index (Optional)**

For better performance with many users, add a reverse index:

```python
# Add to copy_store.py
def users_by_trader(trader_key: str) -> List[int]:
    """Get all users following a specific trader"""
    con = _conn()
    try:
        cur = con.execute("SELECT user_id FROM user_follow_configs WHERE trader_key=?", (trader_key,))
        return [row[0] for row in cur.fetchall()]
    finally:
        con.close()

# Then in your indexer:
from src.services.copytrading.copy_store import users_by_trader

async def on_trader_trade_detected(trader_key: str, trade_data: dict):
    following_users = users_by_trader(trader_key)
    
    for user_id in following_users:
        # ... send signals as above
```

### **3. Signal Format**

The signal dictionary should contain:

```python
signal = {
    "pair": "ETH/USD",           # Trading pair
    "side": "LONG",              # "LONG" or "SHORT"
    "lev": 25,                   # Leverage multiplier
    "notional_usd": 1000.0,      # Total position size in USD
    "collateral_usdc": 40.0      # Collateral in USDC
}
```

### **4. Integration Points**

#### **In Your Indexer Service**
```python
# Example integration point
class TraderIndexer:
    async def process_trade_event(self, event):
        trader_key = event["trader_address"]
        
        # Your existing processing...
        
        # Send copy-trading signals
        await self.send_copy_signals(trader_key, event)
    
    async def send_copy_signals(self, trader_key: str, event: dict):
        from src.services.copytrading.alerts import on_trader_signal
        
        following_users = users_by_trader(trader_key)
        
        signal = {
            "pair": event["pair"],
            "side": event["side"],
            "lev": event["leverage"],
            "notional_usd": event["notional_usd"],
            "collateral_usdc": event["collateral_usdc"]
        }
        
        for user_id in following_users:
            await on_trader_signal(self.bot, user_id, trader_key, signal)
```

#### **In Your Position Tracker**
```python
# Example integration in position tracker
class PositionTracker:
    async def on_position_opened(self, position):
        trader_key = position["trader_key"]
        
        # Send signal for position open
        await self.send_position_signal(trader_key, position, "open")
    
    async def on_position_closed(self, position):
        trader_key = position["trader_key"]
        
        # Send signal for position close
        await self.send_position_signal(trader_key, position, "close")
```

### **5. Daily Digest Integration**

To enable daily digests:

```python
# In your main application startup
from src.services.copytrading.alerts import digest_scheduler

# Start digest scheduler (optional)
asyncio.create_task(digest_scheduler(
    bot=application.bot,
    user_ids=get_active_user_ids(),  # Your function to get active users
    hour_utc=0  # Send at midnight UTC
))
```

### **6. Testing Integration**

Use the development script to test your integration:

```bash
# Set environment variables
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TEST_USER_ID="your_telegram_user_id"
export TEST_TRADER_KEY="trader_address_from_leaderboard"

# Run test
python scripts/dev_fire_signal.py
```

### **7. Monitoring & Debugging**

Monitor the following logs:
- Copy-trading signal processing
- Auto-copy execution results
- Notification delivery status
- Database operations

### **8. Performance Considerations**

- **Reverse Index**: Consider adding `users_by_trader` for O(1) lookups
- **Batch Processing**: For high-frequency traders, batch signals
- **Rate Limiting**: Respect Telegram API rate limits
- **Error Handling**: Ensure failed signals don't block processing

---

This integration maintains the existing architecture while adding powerful copy-trading capabilities.
