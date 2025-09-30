"""API schemas for webhook signals (Phase 6)."""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class SignalIn(BaseModel):
    """Incoming signal from webhook."""

    source: str = Field(..., max_length=64)  # "webhook:tradingview"
    signal_id: str = Field(..., max_length=128)  # provider id or uuid
    tg_user_id: int
    symbol: str
    side: str  # LONG|SHORT|CLOSE
    collateral_usdc: Optional[float] = None
    leverage_x: Optional[int] = None
    reduce_usdc: Optional[float] = None
    slippage_pct: Optional[float] = 0.5
    meta: Optional[dict] = {}

    @field_validator("side")  # type: ignore[misc]
    @classmethod
    def validate_side(cls, v: str) -> str:
        """Validate side is LONG, SHORT, or CLOSE."""
        v = v.upper()
        if v not in {"LONG", "SHORT", "CLOSE"}:
            raise ValueError("side must be LONG, SHORT, or CLOSE")
        return v
