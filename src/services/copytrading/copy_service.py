from __future__ import annotations
from typing import Dict, Any, Optional, Tuple
from decimal import Decimal
import asyncio
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
try:  # pragma: no cover - dynamic import during bootstrap
  from src.services.trading import copy_executor as _copy_executor
except Exception as exc:  # pragma: no cover - optional dependency path
  log.warning("Copy executor import failed", exc_info=exc)
  _copy_executor = None

try:
  from src.database.operations import db
  from src.blockchain.wallet_manager import wallet_manager
except Exception as exc:  # pragma: no cover
  log.warning("Database or wallet manager unavailable", exc_info=exc)
  db = None
  wallet_manager = None

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
    
  if not _executor_ready():
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
    eq = await _calculate_user_equity(uid)
    pct_equity = Decimal(str(cfg.get("pct_equity", 1.0)))
    collateral_usdc = (eq * pct_equity) / Decimal("100")

  # Slippage override
  slip = cfg.get("slippage_override_pct")

  try:
    # call your executor (adapt to your signatures)
    await exec_follow(
      uid=uid,
      trader_key=trader_key,
      pair=signal["pair"],
      side=signal["side"],
      leverage=float(lev),
      collateral_usdc=float(collateral_usdc),
      slippage_pct=float(slip) if slip is not None else None,
    )
    return True, "copied"
  except Exception as e:  # noqa: BLE001
    log.exception("copy_exec_fail", extra={"user_id": uid, "trader_key": trader_key})
    return False, "exec_error"


async def _calculate_user_equity(user_id: int) -> Decimal:
  """Estimate the user's available equity from wallet and open positions."""
  equity = Decimal("0")

  if db is None:
    return Decimal("10000")  # Conservative fallback

  try:
    user = await db.get_user_by_id(user_id)
  except Exception as exc:  # pragma: no cover - defensive
    log.warning("Failed to load user %s for equity calc: %s", user_id, exc)
    user = None

  if user and getattr(user, "wallet_address", None) and wallet_manager:
    try:
      wallet_info = wallet_manager.get_wallet_info(user.wallet_address)
      equity += Decimal(str(wallet_info.get("usdc_balance", 0)))
    except Exception as exc:  # noqa: BLE001
      log.warning("Wallet lookup failed for user %s: %s", user_id, exc)

  try:
    positions = await db.get_user_positions(user_id, status="OPEN")
    for pos in positions:
      size = Decimal(str(pos.size or 0))
      equity += size
  except Exception as exc:  # noqa: BLE001
    log.warning("Failed to aggregate open positions for user %s: %s", user_id, exc)

  return equity if equity > 0 else Decimal("10000")


EXECUTOR_OK = _copy_executor is not None


def executor_available() -> bool:
  """Return True when the async copy executor is wired."""
  available = _copy_executor is not None
  globals()["EXECUTOR_OK"] = available
  return available


def _executor_ready() -> bool:
  # Allow tests to patch exec_follow or EXECUTOR_OK while keeping runtime safety
  if globals().get("EXECUTOR_OK", False):
    return True
  if exec_follow is not executor_follow:
    return True
  return executor_available()


async def executor_status(user_id: int, trader_key: str) -> Dict[str, Any]:
  """Proxy to the async executor status call with graceful fallback."""
  if not executor_available():
    return {"ok": False, "error": "executor_unavailable"}

  try:
    return await _copy_executor.status(user_id, trader_key)
  except Exception as exc:  # pragma: no cover - defensive network/db failure
    log.warning(
      "Executor status failed", extra={"user_id": user_id, "trader_key": trader_key, "error": str(exc)}
    )
    return {"ok": False, "error": str(exc)}


async def executor_follow(
  uid: int,
  trader_key: str,
  pair: str,
  side: str,
  leverage: float,
  collateral_usdc: float,
  slippage_pct: Optional[float] = None,
) -> Dict[str, Any]:
  """Execute a mirror order via the async executor."""
  if not _executor_ready():
    raise RuntimeError("Copy executor unavailable")

  return await _copy_executor.follow(
    user_id=uid,
    trader_key=trader_key,
    pair=pair,
    side=side,
    leverage=leverage,
    collateral_usdc=collateral_usdc,
    slippage_pct=slippage_pct,
  )


# Backwards compatibility aliases for legacy test patches
exec_follow = executor_follow
exec_status = executor_status


async def get_status(uid: int) -> Dict[str, Any]:
  """Aggregate copy trading status for a user from copy_positions data."""
  follows = copy_store.list_follows(uid)
  result: Dict[str, Any] = {
    "follows": [
      {"trader_key": tk, "config": cfg}
      for tk, cfg in follows
    ],
    "aggregate": None,
  }

  if not executor_available():
    return result

  # Fetch aggregate stats
  aggregate = await executor_status(uid, "*")
  result["aggregate"] = aggregate if aggregate.get("ok") else None

  if not follows:
    return result

  async def _leader_status(trader_key: str) -> Dict[str, Any]:
    data = await executor_status(uid, trader_key)
    return data if data.get("ok") else {"ok": False, "error": data.get("error", "unknown")}

  leader_tasks = [
    asyncio.create_task(_leader_status(tk))
    for tk, _ in follows
  ]

  for task, follow in zip(leader_tasks, result["follows"]):
    try:
      follow["status"] = await task
    except Exception as exc:  # pragma: no cover - defensive catch
      follow["status"] = {"ok": False, "error": str(exc)}

  return result
