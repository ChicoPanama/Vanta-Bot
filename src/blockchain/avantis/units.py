"""Unit normalization for Avantis (Phase 3 - single-scaling rule)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizedOrder:
    """Normalized order with single-scaled units."""

    symbol: str  # "BTC-USD"
    side: str  # "LONG"|"SHORT"
    collateral_usdc: int  # 1e6 scaled integer USDC
    leverage_x: int  # 1..500
    size_usd: int  # collateral_usdc * leverage_x, still 1e6 units
    slippage_bps: int  # e.g., 100 = 1.00%


def to_normalized(
    symbol: str,
    side: str,
    collateral_usdc: float,
    leverage_x: int,
    slippage_pct: float,
) -> NormalizedOrder:
    """Convert floats to normalized integers once (single-scaling).

    Args:
        symbol: Market symbol
        side: "LONG" or "SHORT"
        collateral_usdc: Collateral in USDC (float)
        leverage_x: Leverage (integer 1..500)
        slippage_pct: Slippage percentage (e.g., 1.0 for 1%)

    Returns:
        NormalizedOrder with all values as integers

    Rules:
        - USDC amounts: scaled to 1e6 (6 decimals)
        - Slippage: converted to basis points (1% = 100 bps)
        - Size: collateral * leverage (still in 1e6 units)
        - No further scaling after this point
    """
    # Convert floats to ints once
    col_int = int(round(collateral_usdc * 1_000_000))
    size = col_int * int(leverage_x)
    bps = int(round(slippage_pct * 100))  # 1% -> 100 bps

    return NormalizedOrder(
        symbol=symbol.upper(),
        side=side.upper(),
        collateral_usdc=col_int,
        leverage_x=leverage_x,
        size_usd=size,
        slippage_bps=bps,
    )
