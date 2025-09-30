from __future__ import annotations

import json
import logging
import os
import sqlite3
from typing import Any

log = logging.getLogger(__name__)

DEFAULTS = {
    "ui_favorites": ["ETH/USD", "BTC/USD"],
    "default_pair": "ETH/USD",
    "default_slippage_pct": 1.0,
    "lev_presets": [5, 10, 25, 50],
    "collateral_presets": [50, 100, 250, 500],
    "preferred_mode": "DRY",  # UI preference only (informational)
    "linked_wallet": None,  # "0x..." (read-only)
}


class UserPrefs:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or os.getenv("USER_PREFS_DB", "vanta_user_prefs.db")
        self.mem: dict[int, dict[str, Any]] = {}
        try:
            self._ensure_table()
            self.available = True
        except Exception as e:
            log.warning("user_prefs sqlite disabled: %s (falling back to memory)", e)
            self.available = False

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _ensure_table(self):
        con = self._conn()
        try:
            con.execute(
                """
            CREATE TABLE IF NOT EXISTS user_prefs (
                user_id INTEGER PRIMARY KEY,
                data TEXT NOT NULL
            )"""
            )
            con.commit()
        finally:
            con.close()

    def get(self, user_id: int) -> dict[str, Any]:
        if not self.available:
            return self.mem.get(user_id, dict(DEFAULTS))
        con = self._conn()
        try:
            cur = con.execute(
                "SELECT data FROM user_prefs WHERE user_id = ?", (user_id,)
            )
            row = cur.fetchone()
            if not row:
                return dict(DEFAULTS)
            data = json.loads(row[0])
            # backfill any new defaults
            for k, v in DEFAULTS.items():
                data.setdefault(k, v)
            return data
        finally:
            con.close()

    def put(self, user_id: int, prefs: dict[str, Any]):
        # backfill defaults
        for k, v in DEFAULTS.items():
            prefs.setdefault(k, v)
        if not self.available:
            self.mem[user_id] = prefs
            return
        con = self._conn()
        try:
            blob = json.dumps(prefs, separators=(",", ":"), ensure_ascii=False)
            con.execute(
                "INSERT INTO user_prefs(user_id, data) VALUES(?, ?) ON CONFLICT(user_id) DO UPDATE SET data=excluded.data",
                (user_id, blob),
            )
            con.commit()
        finally:
            con.close()


# Global accessor
_store: UserPrefs | None = None


def prefs_store() -> UserPrefs:
    global _store
    if _store is None:
        _store = UserPrefs()
    return _store
