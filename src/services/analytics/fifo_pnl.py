from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal


# Each fill: (side, size, price, fee)
# side: "OPEN" increases position; "CLOSE" decreases (realizes PnL)
def realized_pnl_fifo(
    fills: Iterable[tuple[str, Decimal, Decimal, Decimal]],
) -> Decimal:
    lots: list[tuple[Decimal, Decimal]] = []  # (size, entry_px)
    realized = Decimal("0")
    total_fees = Decimal("0")

    for side, size, price, fee in fills:
        size = abs(size)
        total_fees += fee
        if side == "OPEN":
            lots.append((size, price))
        elif side == "CLOSE":
            remain = size
            while remain > 0 and lots:
                lot_size, lot_px = lots[0]
                take = min(lot_size, remain)
                pnl = (
                    price - lot_px
                ) * take  # long close; adjust sign if short tracking separately
                realized += pnl
                lot_size -= take
                remain -= take
                if lot_size == 0:
                    lots.pop(0)
                else:
                    lots[0] = (lot_size, lot_px)
        # ignore other sides for PnL
    return realized - total_fees
