"""Trading Service business logic built on async database helpers."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from src.blockchain.wallet_manager import wallet_manager
from src.database.models import Position
from src.database.operations import db
from src.services.base_service import BaseService
from src.utils.logging import get_logger
from src.utils.validators import validate_position_data

logger = get_logger(__name__)


class TradingService(BaseService):
    """Service for trading operations backed by async DB access."""

    async def create_position(
        self, user_id: int, position_data: dict[str, Any]
    ) -> Position:
        """Create a new trading position after validating inputs and balance."""
        self.log_operation("create_position", user_id, **position_data)

        validated = validate_position_data(position_data)
        user = await db.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        wallet_info = wallet_manager.get_wallet_info(user.wallet_address)
        required_balance = validated["size"]
        if wallet_info["usdc_balance"] < required_balance:
            raise ValueError(
                f"Insufficient balance. Required: ${required_balance}, "
                f"Available: ${wallet_info['usdc_balance']:.2f}"
            )

        position = await db.create_position(
            user_id=user_id,
            symbol=validated["symbol"],
            side=validated["side"],
            size=validated["size"],
            leverage=validated["leverage"],
        )
        return position

    async def execute_position(self, position_id: int, tx_hash: str) -> Position:
        """Mark a pending position as open once execution succeeds."""
        self.log_operation("execute_position", position_id=position_id, tx_hash=tx_hash)

        position = await db.get_position_by_id(position_id)
        if not position:
            raise ValueError("Position not found")
        if position.status != "PENDING":
            raise ValueError("Position is not in pending status")

        updated = await db.update_position(position_id, status="OPEN", tx_hash=tx_hash)
        if not updated:
            raise ValueError("Failed to update position status")
        return updated

    async def get_user_positions(
        self, user_id: int, status: Optional[str] = None
    ) -> list[Position]:
        """Get user positions with optional status filter."""
        self.log_operation("get_user_positions", user_id, status=status)
        return await db.get_user_positions(user_id, status=status)

    async def update_position_pnl(
        self,
        position_id: int,
        current_price: Decimal,
        pnl: Decimal,
    ) -> Position:
        """Update live position PnL metrics."""
        self.log_operation(
            "update_position_pnl",
            position_id=position_id,
            current_price=current_price,
            pnl=pnl,
        )

        position = await db.get_position_by_id(position_id)
        if not position:
            raise ValueError("Position not found")

        updated = await db.update_position(
            position_id,
            current_price=float(current_price),
            pnl=float(pnl),
        )
        if not updated:
            raise ValueError("Failed to update position")
        return updated

    async def close_position(
        self,
        position_id: int,
        close_price: Decimal,
        pnl: Decimal,
    ) -> Position:
        """Close an open position and persist final metrics."""
        self.log_operation(
            "close_position",
            position_id=position_id,
            close_price=close_price,
            pnl=pnl,
        )

        position = await db.get_position_by_id(position_id)
        if not position:
            raise ValueError("Position not found")
        if position.status != "OPEN":
            raise ValueError("Position is not open")

        updated = await db.update_position(
            position_id,
            status="CLOSED",
            current_price=float(close_price),
            pnl=float(pnl),
            closed_at=datetime.utcnow(),
        )
        if not updated:
            raise ValueError("Failed to close position")
        return updated

    def validate_input(self, data: dict[str, Any]) -> bool:
        """Validate trading input data."""
        try:
            validate_position_data(data)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Position validation failed: {}", exc)
            return False
