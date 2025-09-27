from __future__ import annotations
from decimal import Decimal
from typing import Optional, Dict, Any

class PriceProvider:
    """
    Minimal provider. Replace internals with Avantis Trader SDK price feed callbacks
    (PYTH) or your market data service when ready.
    """
    def __init__(self):
        # simple in-memory last price store; swap with live feed later
        self._last: Dict[str, Decimal] = {}

    async def set_price(self, pair: str, price: Decimal) -> None:
        self._last[pair] = price

    async def get_best_price(self, pair: str) -> Decimal:
        px = self._last.get(pair)
        if px is None:
            # fallback default; replace with SDK/pyth fetch
            return Decimal("1")
        return px

    async def estimate_impact(self, pair: str, notional: Decimal) -> int:
        """
        Return an estimated slippage in basis points for the given notional.
        Replace with Avantis price-impact spread function when wired.
        """
        px = await self.get_best_price(pair)
        if px <= 0:
            return 100  # conservative
        # toy model: 1 bps per $100k notional, capped at 50 bps
        bps = min(int(notional / Decimal("100000")), 50)
        return bps
