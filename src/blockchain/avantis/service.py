"""Avantis integration service facade (Phase 3)."""

import logging
import time
from dataclasses import dataclass
from hashlib import sha256
from typing import Optional

from sqlalchemy.orm import Session
from web3 import Web3

from src.adapters.price.aggregator import PriceAggregator
from src.adapters.price.base import PriceQuote
from src.blockchain.tx.orchestrator import TxOrchestrator
from src.services.contracts.avantis_registry import AvantisRegistry
from src.services.markets.market_catalog import MarketInfo, default_market_catalog

from .calldata import encode_close, encode_open
from .units import to_normalized

logger = logging.getLogger(__name__)


def make_intent_key(
    user_id: int,
    action: str,
    symbol: str,
    side: str | None,
    qty_1e6: int | None,
    price_1e6: int | None = None,
    bucket_s: int = 1,
) -> str:
    """Generate deterministic idempotency key for transaction intent.
    
    Args:
        user_id: User ID
        action: "open" or "close"
        symbol: Market symbol
        side: "LONG" or "SHORT" (None for close)
        qty_1e6: Quantity in 1e6 scaled int
        price_1e6: Price in 1e6 (optional, for limit orders)
        bucket_s: Time bucket in seconds (default 1s to prevent spam)
    
    Returns:
        Deterministic hash string suitable for idempotency key
        
    Note:
        This prevents duplicate transactions by generating the same key
        for identical requests within the time bucket.
    """
    tsb = int(time.time() // bucket_s)
    raw = f"{user_id}|{action}|{symbol}|{side or ''}|{qty_1e6 or 0}|{price_1e6 or 0}|{tsb}"
    return sha256(raw.encode()).hexdigest()


@dataclass
class MarketView:
    """Market view for UX."""

    symbol: str
    min_position_usd_1e6: int
    price: Optional[int]
    price_decimals: int
    source: Optional[str]


class AvantisService:
    """Unified Avantis integration service (Phase 3)."""

    def __init__(self, w3: Web3, db: Session, price_agg: PriceAggregator):
        """Initialize Avantis service.

        Args:
            w3: Web3 instance
            db: Database session
            price_agg: Price aggregator
        """
        self.w3 = w3
        self.db = db
        self.price_agg = price_agg

        # Load market catalog
        self.markets = default_market_catalog()

        logger.info(f"Avantis service initialized with {len(self.markets)} markets")

    def list_markets(self) -> dict[str, MarketView]:
        """List all available markets with current prices.

        Returns:
            Dict mapping symbol to MarketView
        """
        out: dict[str, MarketView] = {}

        for sym, market_info in self.markets.items():
            quote = self.price_agg.get_price(sym)

            out[sym] = MarketView(
                symbol=sym,
                min_position_usd_1e6=market_info.min_position_usd,
                price=quote.price if quote else None,
                price_decimals=quote.decimals if quote else market_info.decimals_price,
                source=quote.source if quote else None,
            )

        return out

    def get_price(self, symbol: str) -> Optional[PriceQuote]:
        """Get current price for symbol.

        Args:
            symbol: Market symbol

        Returns:
            PriceQuote or None
        """
        return self.price_agg.get_price(symbol)

    def open_market(
        self,
        user_id: int,
        symbol: str,
        side: str,
        collateral_usdc: float,
        leverage_x: int,
        slippage_pct: float,
    ) -> str:
        """Open market position.

        Args:
            user_id: User ID (for intent key)
            symbol: Market symbol (e.g., "BTC-USD")
            side: "LONG" or "SHORT"
            collateral_usdc: Collateral amount in USDC
            leverage_x: Leverage (1..500)
            slippage_pct: Slippage percentage (e.g., 1.0 for 1%)

        Returns:
            Transaction hash

        Raises:
            ValueError: If market unknown or below min size
        """
        market = self.markets.get(symbol.upper())
        if not market:
            raise ValueError(f"Unknown market: {symbol}")

        # Normalize units (single-scaling)
        order = to_normalized(symbol, side, collateral_usdc, leverage_x, slippage_pct)

        # Validate min position size
        if order.size_usd < market.min_position_usd:
            min_usd = market.min_position_usd / 1_000_000
            raise ValueError(
                f"Below min position size for {symbol}. "
                f"Min: {min_usd:.2f} USDC, Provided: {order.size_usd / 1_000_000:.2f} USDC"
            )

        # Encode calldata
        to_addr, data = encode_open(self.w3, market.perpetual, order, market.market_id)

        # Execute via orchestrator with deterministic idempotency key
        intent_key = make_intent_key(
            user_id=user_id,
            action="open",
            symbol=symbol,
            side=side,
            qty_1e6=order.size_usd,
        )
        orch = TxOrchestrator(self.w3, self.db)

        logger.info(
            f"Opening {symbol} {side} position: collateral={collateral_usdc} USDC, "
            f"leverage={leverage_x}x, size={order.size_usd / 1_000_000:.2f} USDC"
        )

        return orch.execute(
            intent_key=intent_key, to=to_addr, data=data, value=0, confirmations=2
        )

    def close_market(
        self,
        user_id: int,
        symbol: str,
        reduce_usdc: float,
        slippage_pct: float,
    ) -> str:
        """Close market position (full or partial).

        Args:
            user_id: User ID
            symbol: Market symbol
            reduce_usdc: Amount to reduce in USDC
            slippage_pct: Slippage percentage

        Returns:
            Transaction hash

        Raises:
            ValueError: If market unknown
        """
        market = self.markets.get(symbol.upper())
        if not market:
            raise ValueError(f"Unknown market: {symbol}")

        # Convert to 1e6 scaled integers
        reduce_1e6 = int(round(reduce_usdc * 1_000_000))
        slippage_bps = int(round(slippage_pct * 100))

        # Encode calldata
        to_addr, data = encode_close(
            self.w3, market.perpetual, market.market_id, reduce_1e6, slippage_bps
        )

        # Execute via orchestrator with deterministic idempotency key
        intent_key = make_intent_key(
            user_id=user_id,
            action="close",
            symbol=symbol,
            side=None,
            qty_1e6=reduce_1e6,
        )
        orch = TxOrchestrator(self.w3, self.db)

        logger.info(
            f"Closing {symbol} position: reduce={reduce_usdc} USDC, "
            f"slippage={slippage_pct}%"
        )

        return orch.execute(
            intent_key=intent_key, to=to_addr, data=data, value=0, confirmations=2
        )

    def list_user_positions(self, user_address: str) -> list[dict]:
        """List positions for a user (from indexed data).

        Args:
            user_address: User wallet address

        Returns:
            List of position dicts with cached reads
        """
        from src.repositories.positions_repo import list_positions
        from src.services.cache.positions_cache import PositionsCache

        cache = PositionsCache()
        cached = cache.get_positions(user_address)
        if cached is not None:
            return cached

        rows = list_positions(self.db, user_address)
        out = [
            {
                "symbol": r.symbol,
                "is_long": r.is_long,
                "size_usd_1e6": int(r.size_usd_1e6),
                "collateral_1e6": int(r.entry_collateral_1e6),
                "realized_pnl_1e6": int(r.realized_pnl_1e6),
                "updated_at": r.updated_at.isoformat(),
            }
            for r in rows
        ]

        cache.set_positions(user_address, out)
        return out
