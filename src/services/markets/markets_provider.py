from __future__ import annotations
from typing import List, Optional, Tuple
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

# Try to use your SDK wrapper if present; otherwise fallback
try:
    # Adjust imports if your SDK wrapper lives elsewhere
    from src.integrations.avantis.sdk_client import get_pairs_cache, get_price_for_pair
except Exception as e:  # pragma: no cover - optional dependency path
    logger.warning("Avantis SDK client import failed", exc_info=e)
    get_pairs_cache = None
    get_price_for_pair = None

FALLBACK_PAIRS = [
    "ETH/USD",
    "BTC/USD",
    "SOL/USD",
    "ARB/USD",
    "OP/USD",
    "LINK/USD",
]


async def list_pairs(page: int = 0, page_size: int = 6) -> Tuple[List[str], int]:
    """
    Returns a page of pairs and total_pages.
    Prefers SDK pairs cache; falls back to a static set if unavailable.
    """
    pairs: List[str]
    if callable(get_pairs_cache):
        try:
            pc = await get_pairs_cache()
            # Try attributes commonly used in Avantis SDK wrappers:
            # either objects with .symbol or mapping-like entries
            symbols: List[str] = []
            for p in pc:
                sym = getattr(p, "symbol", None) or getattr(p, "pair", None) or str(p)
                symbols.append(str(sym))
            pairs = [s for s in symbols if s] or FALLBACK_PAIRS
        except Exception as e:  # noqa: BLE001
            logger.warning("Error getting pairs from SDK", exc_info=e)
            pairs = FALLBACK_PAIRS
    else:
        pairs = FALLBACK_PAIRS

    # Normalize (dedupe and limit)
    pairs = list(dict.fromkeys(pairs))[:60]

    total_pages = max(1, (len(pairs) + page_size - 1) // page_size)
    start = max(0, page) * page_size
    return pairs[start : start + page_size], total_pages


async def get_last_price(pair: str) -> Optional[Decimal]:
    if callable(get_price_for_pair):
        try:
            px = await get_price_for_pair(pair)
            return Decimal(str(px)) if px is not None else None
        except Exception as e:  # noqa: BLE001
            logger.warning("Error getting price for pair", extra={"pair": pair}, exc_info=e)
            return None
    return None
