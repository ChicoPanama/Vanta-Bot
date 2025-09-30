# Phase 3: Avantis SDK Hardwiring — COMPLETE ✅

**Branch:** `feat/phase-3-avantis-hardwiring`
**Status:** READY FOR REVIEW
**Tests:** 11/11 passing ✅
**Date:** 2025-09-30

---

## 🎯 Goals

Create a deterministic, unit-safe integration layer for Avantis Protocol that:
- Eliminates double-scaling bugs through single-point normalization
- Uses real price feeds (Chainlink/Pyth) with no mocks in production
- Provides a unified service facade for all Avantis operations
- Generates correct ABI-encoded calldata for the transaction orchestrator
- Validates configurations at startup

---

## 📦 Deliverables

### 1. Market Catalog & Registry
**File:** `src/services/markets/market_catalog.py`

- **MarketInfo dataclass:** Canonical market metadata
- **default_market_catalog():** Loads Base mainnet addresses
- **Markets:** BTC-USD, ETH-USD, SOL-USD
- **Properties:** perpetual address, market ID, min position size, decimals

```python
@dataclass
class MarketInfo:
    symbol: str
    perpetual: str  # Contract address
    market_id: int
    min_position_usd: int  # 1e6 scaled
    decimals_price: int
```

---

### 2. Price Adapters (Real Feeds)
**Files:**
- `src/adapters/price/base.py` - PriceFeed protocol, PriceQuote dataclass
- `src/adapters/price/chainlink_adapter.py` - Chainlink aggregator integration
- `src/adapters/price/pyth_adapter.py` - Pyth Network skeleton (for Phase 7)
- `src/adapters/price/aggregator.py` - Multi-feed fallback strategy

**Chainlink Adapter:**
- Calls `latestRoundData()` on Chainlink aggregators
- Returns integer-scaled prices with decimals
- Validates positive prices
- Handles errors gracefully

**Price Aggregator:**
- Tries feeds in order (Chainlink → Pyth → ...)
- Returns first successful quote
- Logs failures and fallbacks

---

### 3. Unit Normalization (Single-Scaling)
**File:** `src/blockchain/avantis/units.py`

**Key Rule:** Float → Integer conversion happens **once** and **only once**

```python
@dataclass(frozen=True)
class NormalizedOrder:
    symbol: str
    side: str  # "LONG"|"SHORT"
    collateral_usdc: int  # 1e6 scaled
    leverage_x: int
    size_usd: int  # collateral * leverage (1e6)
    slippage_bps: int  # 1% = 100 bps
```

**Function:** `to_normalized(symbol, side, collateral_usdc, leverage_x, slippage_pct)`
- Converts floats to integers with correct scaling
- Uppercases symbol and side
- Frozen dataclass prevents mutation
- No further scaling beyond this point

---

### 4. ABI & Calldata Builders
**Files:**
- `src/blockchain/avantis/abi.py` - Minimal Avantis contract ABIs
- `src/blockchain/avantis/calldata.py` - Calldata encoding functions

**Functions:**
- `encode_open(w3, contract_addr, order, market_id)` → (to, data)
- `encode_close(w3, contract_addr, market_id, reduce_usd_1e6, slippage_bps)` → (to, data)

**Method:**
- Computes function selector from ABI (keccak hash)
- Encodes arguments using `eth_abi.encode()`
- Returns address + calldata bytes for TxOrchestrator

---

### 5. Integration Service Facade
**File:** `src/blockchain/avantis/service.py`

**Class:** `AvantisService`

**Public Methods:**
- `list_markets()` → Dict[str, MarketView]
  - Returns all markets with current prices
- `get_price(symbol)` → Optional[PriceQuote]
  - Get current price for a market
- `open_market(user_id, symbol, side, collateral_usdc, leverage_x, slippage_pct)` → tx_hash
  - Opens position, validates min size, executes via TxOrchestrator
- `close_market(user_id, symbol, reduce_usdc, slippage_pct)` → tx_hash
  - Closes position (full or partial)

**Features:**
- Single entry point for all Avantis operations
- Normalizes units automatically
- Validates market existence and min position size
- Integrates with Phase 2 TxOrchestrator for idempotency + RBF
- Generates unique intent keys per action

---

### 6. UX-Ready Schemas
**File:** `src/bot/schemas/avantis.py`

**Pydantic Models:**
- `OpenRequest`: Validates open position requests
- `CloseRequest`: Validates close position requests

**Validations:**
- Symbol format (uppercase alphanumeric + hyphen)
- Side must be "LONG" or "SHORT"
- Positive amounts
- Leverage 1-500x
- Slippage 0-10%

---

### 7. Startup Validation
**File:** `src/startup/markets_validator.py`

**Function:** `validate_markets_and_feeds(w3)`

**Checks:**
- All perpetual addresses are valid
- Min position sizes are set
- Market IDs are valid
- Fails fast on startup if config is broken

---

## 🧪 Tests

**Total:** 11 tests, 100% passing ✅

### Unit Tests (8)
**`tests/unit/avantis/test_units.py`** (3 tests)
- ✅ Float to integer scaling
- ✅ Uppercase symbol/side
- ✅ Fractional USDC amounts

**`tests/unit/avantis/test_calldata.py`** (2 tests)
- ✅ Encode openPosition calldata
- ✅ Encode closePosition calldata

**`tests/unit/price/test_chainlink_adapter.py`** (3 tests)
- ✅ Get price successfully from Chainlink
- ✅ Return None for unknown symbol
- ✅ Return None for invalid (negative) price

### Integration Tests (3)
**`tests/integration/services/test_avantis_service_validate.py`** (3 tests)
- ✅ Reject unknown market with ValueError
- ✅ Reject below-minimum position size
- ✅ List markets with prices

---

## 📊 Key Metrics

**Files Created:** 12 new files
**Lines Added:** ~800 LOC
**Test Coverage:** 11 tests
**Dependencies:** Uses Phase 2 TxOrchestrator

---

## 🔧 Integration Points

### Depends On:
- **Phase 1:** Secure secrets (KMS signing, encrypted DB)
- **Phase 2:** Transaction orchestrator (idempotency, RBF, nonces)

### Enables:
- **Phase 4-7:** Bot commands, webhooks, monitoring
- **Phase 8-9:** Production hardening, observability

---

## 🚀 Usage Example

```python
from sqlalchemy.orm import Session
from web3 import Web3
from src.blockchain.avantis.service import AvantisService
from src.adapters.price.aggregator import PriceAggregator
from src.adapters.price.chainlink_adapter import ChainlinkAdapter

# Setup
w3 = Web3(Web3.HTTPProvider("https://base-mainnet.example.com"))
db = Session(...)
chainlink = ChainlinkAdapter(w3, {
    "BTC-USD": "0x64c911996D3c6aC71f9b455B1E8E7266BcbD848F"
})
agg = PriceAggregator([chainlink])

# Create service
service = AvantisService(w3, db, agg)

# List markets
markets = service.list_markets()
print(markets["BTC-USD"].price)  # Current BTC price

# Open position
tx_hash = service.open_market(
    user_id=123,
    symbol="BTC-USD",
    side="LONG",
    collateral_usdc=100.0,  # 100 USDC
    leverage_x=5,           # 5x leverage = 500 USD position
    slippage_pct=1.0        # 1% slippage
)
# Returns transaction hash, idempotent, RBF-ready
```

---

## 🛡️ Safety Features

1. **Single-Scaling Rule:** Units converted once, preventing double-scaling bugs
2. **Frozen Dataclasses:** NormalizedOrder is immutable after creation
3. **Startup Validation:** Fails fast if market config is invalid
4. **Min Position Checks:** Rejects positions below Avantis minimums
5. **Unknown Market Protection:** Raises ValueError for invalid symbols
6. **Idempotent Execution:** Uses Phase 2 orchestrator with intent keys
7. **Price Validation:** Rejects negative or zero prices from oracles

---

## 📝 Documentation Updates

- ✅ `PHASE3_SUMMARY.md` (this file)
- ✅ Updated `PROGRESS_CHECKPOINT.md`
- ✅ Code docstrings on all public functions

---

## 🎯 Exit Criteria

All Phase 3 requirements met:

- ✅ **Market registry:** Canonical source for symbols, addresses, IDs
- ✅ **Price adapters:** Real Chainlink integration (Pyth skeleton for Phase 7)
- ✅ **Unit normalization:** Single-scaling rule enforced
- ✅ **Calldata builders:** Correct ABI encoding
- ✅ **Service facade:** Unified public API
- ✅ **UX schemas:** Typed, validated request models
- ✅ **Startup validation:** Config checks on boot
- ✅ **Tests:** 11/11 passing
- ✅ **No mocks in production:** Chainlink adapter is production-ready
- ✅ **Deterministic:** No RNG in pricing or execution logic

---

## 🔄 Promotion Checklist

Before merging:
1. ✅ All tests passing
2. ✅ Lint clean
3. ⏳ PR created with template
4. ⏳ CI green (lint, typecheck, tests, phase gate)
5. ⏳ Manual validation: Deploy to staging, open test position
6. ⏳ Update `PHASE_STATE.md` to `READY_FOR_REVIEW`

---

**Phase 3 Complete — Ready for Human Review! 🚀**
