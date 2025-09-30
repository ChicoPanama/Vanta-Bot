"""Signal rules and risk gating (Phase 6)."""

from dataclasses import dataclass

# Allowed markets and sides (expand via registry)
ALLOWED_SIDES = {"LONG", "SHORT", "CLOSE"}
ALLOWED_SYMBOLS = {"BTC-USD", "ETH-USD", "SOL-USD"}

# Default risk limits
MAX_LEVERAGE = 50
MAX_POSITION_USD_1E6 = 10_000_000_000  # 10k USD


@dataclass
class Decision:
    """Rule evaluation decision."""

    allow: bool
    reason: str | None = None


def evaluate_open(
    db, user_id: int, symbol: str, side: str, collateral_usdc: float, leverage_x: int
) -> Decision:
    """Evaluate open signal against rules.

    Args:
        db: Database session
        user_id: Telegram user ID
        symbol: Market symbol
        side: LONG or SHORT
        collateral_usdc: Collateral amount
        leverage_x: Leverage multiplier

    Returns:
        Decision (allow=True/False with reason)
    """
    if side not in ALLOWED_SIDES:
        return Decision(False, "Side not allowed")

    if symbol not in ALLOWED_SYMBOLS:
        return Decision(False, "Symbol not allowed")

    if leverage_x > MAX_LEVERAGE:
        return Decision(False, f"Leverage>{MAX_LEVERAGE}x")

    size_usd_1e6 = int(round(collateral_usdc * leverage_x * 1_000_000))
    if size_usd_1e6 > MAX_POSITION_USD_1E6:
        return Decision(False, "Exceeds max position")

    # TODO: Check per-user circuit breaker, daily limits, etc.
    # pol = get_or_create_policy(db, user_id)
    # if pol.circuit_breaker: return Decision(False, "Circuit breaker ON")

    return Decision(True)


def evaluate_close(db, user_id: int, symbol: str, reduce_usdc: float) -> Decision:
    """Evaluate close signal against rules.

    Args:
        db: Database session
        user_id: Telegram user ID
        symbol: Market symbol
        reduce_usdc: Reduce amount

    Returns:
        Decision (allow=True/False with reason)
    """
    if symbol not in ALLOWED_SYMBOLS:
        return Decision(False, "Symbol not allowed")

    if reduce_usdc <= 0:
        return Decision(False, "Reduce amount must be positive")

    # TODO: Check user circuit breaker
    # pol = get_or_create_policy(db, user_id)
    # if pol.circuit_breaker: return Decision(False, "Circuit breaker ON")

    return Decision(True)
