# Risk Education Implementation Plan

## Current Trading Flow Analysis

### Existing Open Trade Command
- **Location**: `src/bot/handlers/trading.py`
- **Command**: `/trade` (not `/a_open` as initially assumed)
- **Flow**: 
  1. User selects direction (LONG/SHORT)
  2. User selects asset category (Crypto/Forex)
  3. User selects specific asset
  4. User selects leverage
  5. User inputs position size
  6. User confirms trade
  7. Trade executes via `execute_trade()` function

### Current Execution Path
```
trade_handler() → trade_direction_handler() → asset_selection_handler() 
→ leverage_selection_handler() → size_input_handler() → confirm_trade_handler() 
→ execute_trade()
```

### Risk Education Injection Points

#### 1. **Additive Commands** (Recommended)
- `/analyze <ASSET> <SIZE_USD> <LEVERAGE>` - Educational analysis only
- `/calc <ASSET> <LEVERAGE> [risk_pct]` - Position sizing calculator

#### 2. **Optional Confirmation Overlay** (Future Enhancement)
- Inject risk analysis before `execute_trade()` in `confirm_trade_handler()`
- Show educational summary with inline buttons:
  - `✅ Execute` (proceed with trade)
  - `📊 Analyze deeper` (link to `/analyze`)
  - `❌ Cancel`
- **Never block execution** - only educate and confirm

#### 3. **Integration Points**
- **Portfolio Balance**: Use existing `wallet_manager.get_wallet_info()` 
- **Price Data**: Use existing Avantis SDK `FeedClient` or `PriceProvider`
- **Settings**: Extend existing `src/config/settings.py` with risk education toggles

### Implementation Philosophy
- **Educate, don't restrict** - Never block trades except for technical impossibilities
- **Additive approach** - New commands complement existing `/trade` flow
- **User choice** - Always allow execution after showing risk information
- **Compatible** - Works with existing python-telegram-bot handlers and Avantis SDK

### Technical Compatibility
- ✅ **python-telegram-bot** confirmed (not aiogram)
- ✅ **Avantis SDK integration** preserved
- ✅ **Existing handlers** untouched
- ✅ **Database operations** compatible
- ✅ **Wallet management** integrated

### Risk Calculator Features
- Scenario analysis (0.5%, 1%, 2%, 5%, 10% moves)
- Liquidation distance estimation
- Account risk percentage calculation
- Position quality scoring
- Educational warnings (non-blocking)
- Leverage categorization

### Settings Integration
- Risk education toggles in `env.example` and `settings.py`
- Configurable warning thresholds
- Protocol max leverage display (informational)
- Stress test assumptions

This plan ensures zero disruption to existing functionality while adding comprehensive risk education capabilities.
