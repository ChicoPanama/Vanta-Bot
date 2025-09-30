from __future__ import annotations

from decimal import Decimal


def _to_decimal(x) -> Decimal:
    if isinstance(x, Decimal):
        return x
    if x is None:
        return Decimal("0")
    return Decimal(str(x))


def fmt_usd(x: Decimal | float | int | None) -> str:
    if x is None:
        return "$—"
    d = _to_decimal(x)
    return f"${d:,.2f}"


def fmt_px(x: Decimal | float | int | None, digits: int = 4) -> str:
    if x is None:
        return "—"
    d = _to_decimal(x)
    q = Decimal(10) ** -digits
    return f"{d.quantize(q):,}"
