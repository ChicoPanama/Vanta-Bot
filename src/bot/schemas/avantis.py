"""UX-ready schemas for Avantis actions (Phase 3)."""

from pydantic import BaseModel, Field, field_validator


class OpenRequest(BaseModel):
    """Request to open market position."""

    symbol: str = Field(pattern=r"^[A-Z0-9-]+$")
    side: str  # LONG|SHORT
    collateral_usdc: float = Field(gt=0)
    leverage_x: int = Field(ge=1, le=500)
    slippage_pct: float = Field(ge=0, le=10)

    @field_validator("side")  # type: ignore[misc]
    @classmethod
    def validate_side(cls, v: str) -> str:
        """Validate side is LONG or SHORT."""
        v = v.upper()
        if v not in {"LONG", "SHORT"}:
            raise ValueError("side must be LONG or SHORT")
        return v


class CloseRequest(BaseModel):
    """Request to close market position."""

    symbol: str = Field(pattern=r"^[A-Z0-9-]+$")
    reduce_usdc: float = Field(gt=0)
    slippage_pct: float = Field(ge=0, le=10)
