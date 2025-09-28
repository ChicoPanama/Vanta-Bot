from __future__ import annotations
import os, sqlite3, json, time
from typing import Dict, Any, List, Optional, Tuple

def _db_path() -> str:
  """Resolve DB path from environment at call time to allow test overrides."""
  return os.getenv("USER_PREFS_DB", "vanta_user_prefs.db")

DDL = """
CREATE TABLE IF NOT EXISTS user_follow_configs (
  user_id INTEGER NOT NULL,
  trader_key TEXT NOT NULL,    -- address or hyperliquid/avantis ID string
  cfg_json TEXT NOT NULL,      -- serialized dict of settings
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  PRIMARY KEY(user_id, trader_key)
);
CREATE INDEX IF NOT EXISTS idx_follow_trader ON user_follow_configs(trader_key);
"""

def _conn():
  con = sqlite3.connect(_db_path())
  con.execute("PRAGMA journal_mode=WAL;")
  return con

def init():
  con = _conn()
  try:
    con.executescript(DDL)
    con.commit()
  finally:
    con.close()

DEFAULT_CFG: Dict[str, Any] = {
  "auto_copy": False,
  "notify": True,
  "sizing_mode": "MIRROR",    # MIRROR | FIXED_USD | PCT_EQUITY
  "fixed_usd": 100.0,         # used if FIXED_USD
  "pct_equity": 1.0,          # 1% of equity if PCT_EQUITY
  "max_leverage": 50,
  "slippage_override_pct": None,  # e.g., 1.0
  "per_trade_cap_usd": 500.0,
  "daily_cap_usd": 5000.0,
  "use_loss_protection": True,
  "stop_after_losses": 5,
  "stop_after_drawdown_usd": 1000.0,
  "min_clean_pnl_30d": None,   # informational
  "min_win_rate": None,        # informational
}

def _merge_defaults(cfg: Dict[str, Any]) -> Dict[str, Any]:
  merged = dict(DEFAULT_CFG)
  merged.update(cfg or {})
  return merged

def get(user_id: int, trader_key: str) -> Dict[str, Any]:
  con = _conn()
  try:
    cur = con.execute("SELECT cfg_json FROM user_follow_configs WHERE user_id=? AND trader_key=?",
                      (user_id, trader_key))
    row = cur.fetchone()
    if not row: return dict(DEFAULT_CFG)
    cfg = json.loads(row[0])
    return _merge_defaults(cfg)
  finally:
    con.close()

def put(user_id: int, trader_key: str, cfg: Dict[str, Any]) -> None:
  now = int(time.time())
  data = json.dumps(_merge_defaults(cfg), separators=(",", ":"), ensure_ascii=False)
  con = _conn()
  try:
    con.execute(
      "INSERT INTO user_follow_configs(user_id, trader_key, cfg_json, created_at, updated_at) "
      "VALUES(?,?,?,?,?) "
      "ON CONFLICT(user_id, trader_key) DO UPDATE SET cfg_json=excluded.cfg_json, updated_at=excluded.updated_at",
      (user_id, trader_key, data, now, now)
    )
    con.commit()
  finally:
    con.close()

def remove(user_id: int, trader_key: str) -> None:
  con = _conn()
  try:
    con.execute("DELETE FROM user_follow_configs WHERE user_id=? AND trader_key=?",
                (user_id, trader_key))
    con.commit()
  finally:
    con.close()

def list_follows(user_id: int) -> List[Tuple[str, Dict[str, Any]]]:
  con = _conn()
  try:
    cur = con.execute("SELECT trader_key, cfg_json FROM user_follow_configs WHERE user_id=? ORDER BY trader_key",
                      (user_id,))
    out = []
    for k, v in cur.fetchall():
      out.append((k, _merge_defaults(json.loads(v))))
    return out
  finally:
    con.close()

def users_by_trader(trader_key: str) -> List[int]:
  """Get all users following a specific trader"""
  con = _conn()
  try:
    cur = con.execute("SELECT user_id FROM user_follow_configs WHERE trader_key=?", (trader_key,))
    return [row[0] for row in cur.fetchall()]
  finally:
    con.close()

def all_trader_keys() -> List[str]:
  """Get all unique trader keys for maintenance ops"""
  con = _conn()
  try:
    cur = con.execute("SELECT DISTINCT trader_key FROM user_follow_configs ORDER BY trader_key")
    return [row[0] for row in cur.fetchall()]
  finally:
    con.close()
