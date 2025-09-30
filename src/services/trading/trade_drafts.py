from __future__ import annotations

import time
from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class TradeDraft:
    user_id: int
    pair: str
    side: str | None = None  # "LONG" | "SHORT"
    leverage: Decimal | None = None
    collateral_usdc: Decimal | None = None
    ts: float = field(default_factory=lambda: time.time())


class DraftStore:
    """Simple in-memory store; we can swap to Redis later without changing handlers."""

    def __init__(self) -> None:
        self._d: dict[str, TradeDraft] = {}

    @staticmethod
    def _key(user_id: int) -> str:
        return f"draft:{user_id}"

    def get(self, user_id: int) -> TradeDraft | None:
        return self._d.get(self._key(user_id))

    def put(self, draft: TradeDraft) -> None:
        self._d[self._key(draft.user_id)] = draft

    def clear(self, user_id: int) -> None:
        self._d.pop(self._key(user_id), None)


draft_store = DraftStore()
