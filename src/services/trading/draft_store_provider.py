# src/services/trading/draft_store_provider.py
from __future__ import annotations
import asyncio
_store = None
async def init(store_factory):
    global _store
    _store = await store_factory()
def store():
    return _store
