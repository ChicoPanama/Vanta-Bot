"""Central application configuration using typed environment settings."""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # Environment & logging
    ENVIRONMENT: str = Field("development", env="ENVIRONMENT")
    DEBUG: bool = Field(False, env="DEBUG")
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    LOG_JSON: bool = Field(False, env="LOG_JSON")

    # Telegram / bot
    TELEGRAM_BOT_TOKEN: str | None = Field(None, env="TELEGRAM_BOT_TOKEN")

    # Blockchain / Base network
    BASE_RPC_URL: str = Field("https://mainnet.base.org", env="BASE_RPC_URL")
    BASE_CHAIN_ID: int = Field(8453, env="BASE_CHAIN_ID")
    BASE_WS_URL: str | None = Field(None, env="BASE_WS_URL")

    # Data stores
    DATABASE_URL: str = Field("sqlite+aiosqlite:///vanta_bot.db", env="DATABASE_URL")
    REDIS_URL: str = Field("redis://localhost:6379/0", env="REDIS_URL")

    # Security & secrets
    ENCRYPTION_KEY: str | None = Field(None, env="ENCRYPTION_KEY")
    TRADER_PRIVATE_KEY: str | None = Field(None, env="TRADER_PRIVATE_KEY")

    # Signing backends (Phase 1: KMS-first)
    SIGNER_BACKEND: str = Field("kms", env="SIGNER_BACKEND")  # kms|local
    PRIVATE_KEY: str | None = Field(None, env="PRIVATE_KEY")  # dev only
    KMS_KEY_ID: str | None = Field(None, env="KMS_KEY_ID")  # AWS KMS key ID
    AWS_KMS_KEY_ID: str | None = Field(None, env="AWS_KMS_KEY_ID")  # Legacy compat
    AWS_REGION: str = Field("us-east-1", env="AWS_REGION")

    # Envelope encryption (Phase 1)
    ENCRYPTION_CONTEXT_APP: str = Field("vanta-bot", env="ENCRYPTION_CONTEXT_APP")
    ENCRYPTION_DEK_BYTES: int = Field(32, env="ENCRYPTION_DEK_BYTES")  # 256-bit DEK

    # Key vault settings
    LOCAL_WRAP_KEY_B64: str | None = Field(None, env="LOCAL_WRAP_KEY_B64")
    KEY_ENVELOPE_ENABLED: bool = Field(False, env="KEY_ENVELOPE_ENABLED")

    # Contracts / protocol
    AVANTIS_TRADING_CONTRACT: str | None = Field(None, env="AVANTIS_TRADING_CONTRACT")
    AVANTIS_VAULT_CONTRACT: str | None = Field(None, env="AVANTIS_VAULT_CONTRACT")
    USDC_CONTRACT: str = Field(
        "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", env="USDC_CONTRACT"
    )

    # Copy trading / execution
    COPY_EXECUTION_MODE: str = Field("DRY", env="COPY_EXECUTION_MODE")
    DEFAULT_SLIPPAGE_PCT: float = Field(1.0, env="DEFAULT_SLIPPAGE_PCT")
    MAX_LEVERAGE: int = Field(500, env="MAX_LEVERAGE")
    MAX_COPY_LEVERAGE: int = Field(100, env="MAX_COPY_LEVERAGE")
    MIN_POSITION_SIZE: int = Field(1, env="MIN_POSITION_SIZE")
    MAX_POSITION_SIZE: int = Field(100_000, env="MAX_POSITION_SIZE")

    # Leaderboard / eligibility thresholds
    LEADER_ACTIVE_HOURS: int = Field(72, env="LEADER_ACTIVE_HOURS")
    LEADER_MIN_TRADES_30D: int = Field(300, env="LEADER_MIN_TRADES_30D")
    LEADER_MIN_VOLUME_30D_USD: int = Field(10_000_000, env="LEADER_MIN_VOLUME_30D_USD")

    # Indexer settings (initial default)
    INDEXER_BACKFILL_RANGE_INITIAL: int = Field(
        1000, env="INDEXER_BACKFILL_RANGE"
    )  # Number of blocks to backfill

    # Rate limiting & monitoring
    COPY_EXECUTION_RATE_LIMIT: int = Field(10, env="COPY_EXECUTION_RATE_LIMIT")
    TELEGRAM_MESSAGE_RATE_LIMIT: int = Field(30, env="TELEGRAM_MESSAGE_RATE_LIMIT")
    ENABLE_METRICS: bool = Field(True, env="ENABLE_METRICS")
    SENTRY_DSN: str | None = Field(None, env="SENTRY_DSN")

    # Admin & control flags (accept CSV strings in env for tests)
    ADMIN_USER_IDS: list[int] | str = Field(default_factory=list)
    SUPER_ADMIN_IDS: list[int] | str = Field(default_factory=list)

    EMERGENCY_STOP: bool = Field(False, env="EMERGENCY_STOP")
    EMERGENCY_STOP_COPY_TRADING: bool = Field(False, env="EMERGENCY_STOP_COPY_TRADING")
    PAUSE_NEW_FOLLOWS: bool = Field(False, env="PAUSE_NEW_FOLLOWS")
    MAINTENANCE_MODE: bool = Field(False, env="MAINTENANCE_MODE")

    # Health & diagnostics
    HEALTH_PORT: int = Field(8080, env="HEALTH_PORT")

    # Indexer / backfill configuration
    INDEXER_BACKFILL_RANGE: int = Field(50_000, env="INDEXER_BACKFILL_RANGE")

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, extra="ignore"
    )

    # ------------------------------------------------------------------
    # Validators / helpers

    @field_validator("DEBUG", mode="before")
    def _normalize_debug(cls, value: object) -> bool:
        # Accept only explicit booleans or 'true'/'false'; ignore other truthy strings
        # In pytest, default to False unless DEBUG explicitly set in env
        if os.getenv("PYTEST_CURRENT_TEST") and "DEBUG" not in os.environ:
            return False
        if isinstance(value, bool):
            # If pytest and DEBUG not set, force False even if prior global leaked True
            if os.getenv("PYTEST_CURRENT_TEST") and "DEBUG" not in os.environ:
                return False
            return value
        if value is None:
            return False
        s = str(value).strip().lower()
        if s in {"true", "false"}:
            return s == "true"
        return False

    @field_validator("DATABASE_URL", mode="before")
    def _ensure_async_sqlalchemy_url(cls, value: str) -> str:
        """Force async driver for sqlite URLs so SQLAlchemy async works."""
        if value and value.startswith("sqlite:///") and "+aiosqlite" not in value:
            return value.replace("sqlite:///", "sqlite+aiosqlite:///")
        return value

    @field_validator("ADMIN_USER_IDS", "SUPER_ADMIN_IDS", mode="before")
    def _parse_int_list(cls, value):
        if not value:
            return []
        # Accept JSON array, Python list, or CSV string; invalid -> []
        try:
            if isinstance(value, list):
                return [int(v) for v in value]
            s = str(value).strip()
            # Try JSON array first
            if s.startswith("[") and s.endswith("]"):
                import json

                arr = json.loads(s)
                return [int(v) for v in arr]
            # Fallback to CSV (strict: any non-digit token => empty list)
            parts = [p.strip() for p in s.split(",") if p.strip()]
            if not parts:
                return []
            if any(not p.isdigit() for p in parts):
                return []
            return [int(p) for p in parts]
        except Exception:
            return []

    @field_validator("COPY_EXECUTION_MODE", mode="before")
    def _normalise_execution_mode(cls, value: str) -> str:
        value = (value or "DRY").upper().strip()
        if value not in {"DRY", "LIVE"}:
            raise ValueError("COPY_EXECUTION_MODE must be either 'DRY' or 'LIVE'")
        return value

    @field_validator("SIGNER_BACKEND", mode="before")
    def _validate_signer_backend(cls, value: str) -> str:
        """Validate signer backend is kms or local."""
        value = (value or "kms").lower().strip()
        if value not in {"kms", "local"}:
            raise ValueError("SIGNER_BACKEND must be either 'kms' or 'local'")
        return value

    # ------------------------------------------------------------------
    # Compatibility helpers (mirroring previous API)

    def validate(self) -> bool:
        """Validate required configuration at startup."""
        runtime_mode = os.getenv("RUNTIME_MODE", "BOT").upper()

        core_required = [
            "TELEGRAM_BOT_TOKEN",
            "DATABASE_URL",
            "BASE_RPC_URL",
            "ENCRYPTION_KEY",
        ]
        bot_required = core_required + ["REDIS_URL"]
        indexer_required = core_required + ["AVANTIS_TRADING_CONTRACT"]
        sdk_required = core_required + ["AVANTIS_TRADING_CONTRACT", "USDC_CONTRACT"]

        if runtime_mode == "INDEXER":
            required = indexer_required
        elif runtime_mode == "SDK":
            required = sdk_required
        else:
            required = bot_required

        missing = [name for name in required if not getattr(self, name)]
        if missing:
            raise ValueError(
                f"Missing required configuration fields for {runtime_mode} mode: {', '.join(missing)}"
            )
        return True

    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in {"production", "prod"}

    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() in {"development", "dev", "local"}

    def is_dry_mode(self) -> bool:
        return self.COPY_EXECUTION_MODE == "DRY"

    def is_live_mode(self) -> bool:
        return self.COPY_EXECUTION_MODE == "LIVE"

    def build_key_vault(self):
        """Build key vault service based on configuration."""
        if self.AWS_KMS_KEY_ID:
            try:
                import boto3

                kms_client = boto3.client("kms", region_name=self.AWS_REGION)
                from src.security.key_vault import AwsKmsKeyVault

                return AwsKmsKeyVault(
                    kms_key_id=self.AWS_KMS_KEY_ID, kms_client=kms_client
                )
            except ImportError:
                raise ValueError("boto3 required for AWS KMS key vault")

        if self.LOCAL_WRAP_KEY_B64:
            from src.security.key_vault import LocalFernetKeyVault

            return LocalFernetKeyVault(self.LOCAL_WRAP_KEY_B64)

        raise ValueError(
            "Either AWS_KMS_KEY_ID or LOCAL_WRAP_KEY_B64 must be configured"
        )

    # ------------------------------------------------------------------
    # Compatibility properties (legacy lower-case accessors)

    @property
    def default_slippage_pct(self) -> float:
        """Legacy accessor used by some handlers/services."""
        return self.DEFAULT_SLIPPAGE_PCT

    @property
    def trading_contract(self) -> str | None:
        """Legacy accessor mapping to AVANTIS_TRADING_CONTRACT."""
        return self.AVANTIS_TRADING_CONTRACT

    @property
    def vault_contract(self) -> str | None:
        return self.AVANTIS_VAULT_CONTRACT

    @property
    def log_json(self) -> bool:
        return self.LOG_JSON

    def runtime_summary(self) -> str:
        """Return a redacted runtime summary safe for logging."""
        # Normalize schemes for backwards-compatible display
        db_url = self.DATABASE_URL or ""
        if db_url.startswith("sqlite+"):
            db_display = "sqlite://..."
        else:
            db_display = f"{db_url.split(':', 1)[0]}://..." if ":" in db_url else db_url

        redis_url = self.REDIS_URL or ""
        redis_display = (
            f"{redis_url.split(':', 1)[0]}://..." if ":" in redis_url else redis_url
        )

        contract_preview = (
            f"{self.AVANTIS_TRADING_CONTRACT[:12]}..."
            if self.AVANTIS_TRADING_CONTRACT
            else "Not set"
        )

        return (
            "Configuration Summary:\n"
            f"- Environment: {self.ENVIRONMENT}\n"
            f"- Debug: {self.DEBUG}\n"
            f"- Log Level: {self.LOG_LEVEL}\n"
            f"- Database: {db_display}\n"
            f"- Redis: {redis_display}\n"
            f"- Base RPC: {self.BASE_RPC_URL}\n"
            f"- Trading Contract: {contract_preview}\n"
            f"- Copy Mode: {self.COPY_EXECUTION_MODE}\n"
            f"- Emergency Stop: {self.EMERGENCY_STOP}\n"
            f"- Leader Min Trades: {self.LEADER_MIN_TRADES_30D}\n"
            f"- Leader Min Volume: ${int(self.LEADER_MIN_VOLUME_30D_USD):,}"
        )


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()


# Singleton instances expected across the codebase
settings: Settings = get_settings()
config: Settings = settings  # Backwards compatibility alias


class Config(Settings):  # legacy compatibility: behave like Settings
    pass


__all__ = ["Settings", "settings", "config", "get_settings", "Config"]
