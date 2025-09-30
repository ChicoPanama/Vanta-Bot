"""Telegram formatting utilities (Phase 5)."""


def fmt_addr(addr: str | None) -> str:
    """Format address for display.

    Args:
        addr: Ethereum address

    Returns:
        Shortened address (0x1234...5678) or —
    """
    if not addr:
        return "—"
    return f"{addr[:6]}…{addr[-4:]}"


def h1(text: str) -> str:
    """Format header."""
    return f"*{text}*"


def code(text: str) -> str:
    """Format as code."""
    return f"`{text}`"


def ok(text: str) -> str:
    """Format success message."""
    return f"✅ {text}"


def warn(text: str) -> str:
    """Format warning message."""
    return f"⚠️ {text}"


def usdc1e6(amount: int) -> str:
    """Format 1e6-scaled USDC amount.

    Args:
        amount: Amount in 1e6 units

    Returns:
        Formatted string (e.g., "10.50 USDC")
    """
    return f"{amount / 1_000_000:.2f} USDC"
