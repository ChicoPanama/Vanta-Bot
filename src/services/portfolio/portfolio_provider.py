from __future__ import annotations

from decimal import Decimal


class PortfolioProvider:
    """
    Stub that pretends we track user equity & leverage. Replace with your real wallet/
    margin state once your Avantis account client is plugged in.
    """

    async def get_equity(self, user_id: int) -> Decimal:
        # placeholder: $10,000
        return Decimal("10000")

    async def get_leverage(self, user_id: int) -> Decimal:
        # placeholder: 2x
        return Decimal("2")
