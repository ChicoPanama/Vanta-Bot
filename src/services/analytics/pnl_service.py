from __future__ import annotations

from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.engine import Engine

from .fifo_pnl import realized_pnl_fifo


class PnlService:
    def __init__(self, engine: Engine):
        self.engine = engine

    def clean_realized_pnl_30d(self, address: str) -> Decimal:
        sql = text(
            """
            select side, is_long, size, price, fee
            from fills
            where address = :addr
              and ts >= (strftime('%s', 'now') - 30 * 24 * 60 * 60)
            order by ts asc, id asc
        """
        )
        with self.engine.begin() as conn:
            rows = [
                dict(r._mapping) for r in conn.execute(sql, {"addr": address.lower()})
            ]

        # Split by direction for correct sign handling
        long_stream = []
        short_stream = []
        for r in rows:
            side = str(r["side"]).upper()
            size = Decimal(str(r["size"]))
            price = Decimal(str(r["price"]))
            fee = Decimal(str(r["fee"] or 0))
            if r["is_long"]:
                long_stream.append((side, size, price, fee))
            else:
                # for shorts: invert PnL direction
                short_stream.append((side, size, price, fee))

        pnl_long = realized_pnl_fifo(long_stream)
        # For shorts, flip PnL formula: reuse fifo by flipping OPEN/CLOSE semantics
        # or compute with sign-adjustment directly. Simple approach: map price delta reversed.
        # Quick fix: reinterpret CLOSE as realize (lot_px - price)
        # We'll hack by negating price for consistency is not precise; better is duplicate function.
        # For clarity here, recompute:
        pnl_short = Decimal("0")
        lots = []
        for side, size, price, fee in short_stream:
            if side == "OPEN":
                lots.append((size, price))
            elif side == "CLOSE":
                remain = size
                while remain > 0 and lots:
                    lot_size, lot_px = lots[0]
                    take = min(lot_size, remain)
                    pnl_short += (
                        lot_px - price
                    ) * take  # short benefits when price drops
                    lot_size -= take
                    remain -= take
                    if lot_size == 0:
                        lots.pop(0)
                    else:
                        lots[0] = (lot_size, lot_px)
            pnl_short -= fee

        return pnl_long + pnl_short
