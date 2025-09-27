from __future__ import annotations
from typing import Dict, Any, Optional, Tuple
from decimal import Decimal
import logging
import os

from src.services.copytrading import copy_store
log = logging.getLogger(__name__)

# Import server mode check
try:
  from src.config.flags_standalone import is_live
except ImportError:
  # Fallback if flags_standalone not available
  def is_live():
    return os.getenv("COPY_EXECUTION_MODE", "DRY").upper() == "LIVE"

# Optional imports (graceful fallback)
try:
  from src.services.trading.copy_executor import follow as exec_follow
  from src.services.trading.copy_executor import status as exec_status
  EXECUTOR_OK = True
except Exception:
  EXECUTOR_OK = False

def init():
  copy_store.init()

def get_cfg(uid: int, trader_key: str) -> Dict[str, Any]:
  return copy_store.get(uid, trader_key)

def set_cfg(uid: int, trader_key: str, cfg: Dict[str, Any]) -> None:
  copy_store.put(uid, trader_key, cfg)

def unfollow(uid: int, trader_key: str) -> None:
  copy_store.remove(uid, trader_key)

def list_follows(uid: int):
  return copy_store.list_follows(uid)

async def maybe_autocopy_on_signal(
  uid: int,
  trader_key: str,
  signal: Dict[str, Any],   # {pair, side, notional_usd, lev, ...}
) -> Tuple[bool, str]:
  cfg = copy_store.get(uid, trader_key)
  if not cfg.get("auto_copy"):
    return False, "auto_copy_off"
  
  # Server LIVE guard - never execute if server is in DRY mode
  if not is_live():
    return False, "server_dry"
    
  if not EXECUTOR_OK:
    return False, "executor_missing"

  # Enforce caps
  notional = Decimal(str(signal.get("notional_usd", "0")))
  if cfg.get("per_trade_cap_usd") and notional > Decimal(str(cfg["per_trade_cap_usd"])):
    return False, "over_per_trade_cap"

  # Compute copy sizing (simplified; refine as your portfolio provider is available)
  sizing = cfg.get("sizing_mode", "MIRROR")
  collateral_usdc = Decimal("0")
  lev = Decimal(str(signal.get("lev", "1")))

  if sizing == "MIRROR":
    collateral_usdc = Decimal(str(signal.get("collateral_usdc", "0")))
  elif sizing == "FIXED_USD":
    collateral_usdc = Decimal(str(cfg.get("fixed_usd", 100.0))) / (lev if lev > 0 else Decimal("1"))
  else:  # PCT_EQUITY
    eq = Decimal("10000")  # TODO: replace with real equity provider
    collateral_usdc = (eq * Decimal(str(cfg.get("pct_equity", 1.0))) / Decimal("100")) / (lev if lev > 0 else Decimal("1"))

  # Slippage override
  slip = cfg.get("slippage_override_pct")

  try:
    # call your executor (adapt to your signatures)
    await exec_follow(
      user_id=uid,
      trader_key=trader_key,
      pair=signal["pair"],
      side=signal["side"],
      leverage=float(lev),
      collateral_usdc=float(collateral_usdc),
      slippage_pct=float(slip) if slip is not None else None
    )
    return True, "copied"
  except Exception as e:
    log.exception("copy_exec_fail: %s", e)
    return False, "exec_error"
