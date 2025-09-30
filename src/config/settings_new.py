from __future__ import annotations

import os
from dataclasses import dataclass, field


def _get(name: str, default: str | None = None, required: bool = False) -> str | None:
    val = os.getenv(name, default)
    if required and (val is None or val == ""):
        raise RuntimeError(f"Missing required env: {name}")
    return val


@dataclass
class Settings:
    # Core/runtime
    env: str = _get("ENV", "dev")
    base_rpc_url: str = _get("BASE_RPC_URL", "https://mainnet.base.org", required=True)
    base_chain_id: int = int(_get("BASE_CHAIN_ID", "8453") or "8453")
    database_url: str = _get("DATABASE_URL", "sqlite:///vanta_bot.db")
    redis_url: str = _get("REDIS_URL", "redis://localhost:6379/0")
    telegram_bot_token: str | None = _get("TELEGRAM_BOT_TOKEN")

    # Avantis / contracts
    usdc_contract: str = _get(
        "USDC_CONTRACT", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
    )
    trading_contract: str | None = _get("AVANTIS_TRADING_CONTRACT")
    vault_contract: str | None = _get("AVANTIS_VAULT_CONTRACT")

    # Execution & feeds
    copy_execution_mode: str = _get("COPY_EXECUTION_MODE", "DRY")  # DRY | LIVE
    default_slippage_pct: float = float(_get("DEFAULT_SLIPPAGE_PCT", "1"))
    pyth_ws_url: str | None = _get("PYTH_WS_URL")

    # Admins & logging
    admins: set[int] = field(
        default_factory=lambda: set(
            map(int, filter(None, (_get("ADMINS", "") or "").split(",")))
        )
    )
    log_json: bool = (_get("LOG_JSON", "false") or "false").lower() == "true"


settings = Settings()


def runtime_summary() -> str:
    return (
        f"env={settings.env} chain={settings.base_chain_id} "
        f"mode={settings.copy_execution_mode} "
        f"db={'set' if settings.database_url else 'missing'} "
        f"redis={'set' if settings.redis_url else 'missing'}"
    )
