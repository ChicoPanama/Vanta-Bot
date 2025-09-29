"""
Strict data models for Avantis trading.

This module defines the core data structures used throughout the application,
ensuring type safety and validation at the boundaries.
"""

from typing import TypedDict, NamedTuple, Optional
from decimal import Decimal
from enum import Enum


class OrderType(Enum):
    """Order types supported by the protocol."""
    MARKET = 0
    LIMIT = 1


class PositionDirection(Enum):
    """Position direction."""
    LONG = True
    SHORT = False


class TradeInput(TypedDict):
    """
    Input parameters for opening a trade.
    
    All values are in contract units (scaled).
    """
    pairIndex: int
    buy: bool
    leverage: int          # 1e10 scale
    initialPosToken: int   # USDC 6dp
    positionSizeUSDC: int  # USDC 6dp
    openPrice: int         # 0 for market orders
    tp: int               # Take profit price (0 = no TP)
    sl: int               # Stop loss price (0 = no SL)
    timestamp: int        # Timestamp (0 = current)


class TradeLimits(TypedDict):
    """Contract limits for trading parameters."""
    minPositionSize: int
    maxPositionSize: int
    maxLeverage: int
    maxSlippage: int
    maxPairs: int


class PairInfo(TypedDict):
    """Information about a trading pair."""
    pairIndex: int
    baseAsset: str
    quoteAsset: str
    isActive: bool
    minPositionSize: int
    maxPositionSize: int
    maxLeverage: int


class HumanTradeParams(NamedTuple):
    """Human-readable trade parameters."""
    collateral_usdc: Decimal
    leverage_x: Decimal
    slippage_pct: Decimal
    pair_index: int
    is_long: bool
    order_type: OrderType


class TradeResult(NamedTuple):
    """Result of a trade execution."""
    success: bool
    transaction_hash: Optional[str]
    error_message: Optional[str]
    gas_used: Optional[int]
    block_number: Optional[int]


class ContractStatus(NamedTuple):
    """Current status of the trading contract."""
    is_paused: bool
    operator: str
    max_slippage: int
    pair_infos_address: str
    last_updated: float


class WalletInfo(NamedTuple):
    """Wallet information for trading."""
    address: str
    eth_balance: Decimal
    usdc_balance: Decimal
    is_connected: bool


class PriceInfo(NamedTuple):
    """Price information for a trading pair."""
    pair_index: int
    price: Decimal
    timestamp: float
    source: str  # e.g., "chainlink", "pyth"


class RiskLimits(NamedTuple):
    """Risk management limits."""
    max_position_size_usd: Decimal
    max_account_risk_pct: Decimal
    liquidation_buffer_pct: Decimal
    max_daily_loss_pct: Decimal
