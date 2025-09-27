from __future__ import annotations
import os, json, time
from decimal import Decimal
from typing import Optional
try:
    import aioredis  # aioredis==2+
except Exception as e:
    logger.warning(f"aioredis import failed: {e}")
    aioredis = None

from src.services.trading.trade_drafts import TradeDraft, DraftStore as MemoryStore

REDIS_URL = os.getenv("REDIS_URL", "")
TTL = int(os.getenv("DRAFT_TTL_SEC", "1800"))

class RedisDraftStore:
    def __init__(self, url: str):
        self.url = url
        self._r = None

    async def _client(self):
        if self._r is None:
            self._r = await aioredis.from_url(self.url, encoding="utf-8", decode_responses=True)
        return self._r

    def _key(self, user_id: int) -> str:
        return f"draft:{user_id}"

    async def get(self, user_id: int) -> Optional[TradeDraft]:
        r = await self._client()
        raw = await r.get(self._key(user_id))
        if not raw:
            return None
        d = json.loads(raw)
        return TradeDraft(
            user_id=user_id,
            pair=d.get("pair"),
            side=d.get("side"),
            leverage=Decimal(d["leverage"]) if d.get("leverage") else None,
            collateral_usdc=Decimal(d["collateral_usdc"]) if d.get("collateral_usdc") else None,
            ts=d.get("ts", time.time()),
        )

    async def put(self, draft: TradeDraft):
        r = await self._client()
        payload = {
            "pair": draft.pair,
            "side": draft.side,
            "leverage": str(draft.leverage) if draft.leverage else None,
            "collateral_usdc": str(draft.collateral_usdc) if draft.collateral_usdc else None,
            "ts": draft.ts,
        }
        await r.set(self._key(draft.user_id), json.dumps(payload), ex=TTL)

    async def clear(self, user_id: int):
        r = await self._client()
        await r.delete(self._key(user_id))

# factory
async def get_draft_store():
    if REDIS_URL and aioredis:
        return RedisDraftStore(REDIS_URL)
    # fallback to memory store (sync interface)
    return MemoryStore()
