"""Positions repository for Phase 4 persistence."""

from collections.abc import Iterable
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from src.database.models import IndexedFill, UserPosition


def get_position(db: Session, user_addr: str, symbol: str) -> Optional[UserPosition]:
    """Get user position for a symbol.

    Args:
        db: Database session
        user_addr: User wallet address
        symbol: Market symbol (e.g., "BTC-USD")

    Returns:
        UserPosition or None if not found
    """
    return (
        db.query(UserPosition)
        .filter_by(user_address=user_addr.lower(), symbol=symbol.upper())
        .one_or_none()
    )


def upsert_position(
    db: Session,
    user_addr: str,
    symbol: str,
    is_long: bool,
    size_delta_1e6: int,
    collateral_delta_1e6: int,
    realized_pnl_delta_1e6: int = 0,
) -> UserPosition:
    """Update or create user position.

    Args:
        db: Database session
        user_addr: User wallet address
        symbol: Market symbol
        is_long: Position direction
        size_delta_1e6: Change in position size (1e6 scaled)
        collateral_delta_1e6: Change in collateral (1e6 scaled)
        realized_pnl_delta_1e6: Change in realized PnL (1e6 scaled)

    Returns:
        Updated UserPosition
    """
    pos = get_position(db, user_addr, symbol)
    if not pos:
        pos = UserPosition(
            user_address=user_addr.lower(),
            symbol=symbol.upper(),
            is_long=is_long,
            size_usd_1e6=0,
            entry_collateral_1e6=0,
            realized_pnl_1e6=0,
        )
        db.add(pos)

    # Update position (keep size non-negative)
    pos.size_usd_1e6 = max(0, pos.size_usd_1e6 + size_delta_1e6)
    pos.entry_collateral_1e6 = max(0, pos.entry_collateral_1e6 + collateral_delta_1e6)
    pos.realized_pnl_1e6 += realized_pnl_delta_1e6
    pos.is_long = is_long
    pos.updated_at = datetime.utcnow()

    db.add(pos)
    db.commit()
    db.refresh(pos)
    return pos


def list_positions(db: Session, user_addr: str) -> list[UserPosition]:
    """List all positions for a user.

    Args:
        db: Database session
        user_addr: User wallet address

    Returns:
        List of UserPosition objects
    """
    return (
        db.query(UserPosition)
        .filter_by(user_address=user_addr.lower())
        .filter(UserPosition.size_usd_1e6 > 0)  # Only active positions
        .all()
    )


def insert_fills(db: Session, rows: Iterable[IndexedFill]) -> None:
    """Bulk insert fill records.

    Args:
        db: Database session
        rows: Iterable of IndexedFill objects
    """
    for fill in rows:
        db.add(fill)
    db.commit()


def get_fills_for_user(
    db: Session, user_addr: str, symbol: Optional[str] = None, limit: int = 100
) -> list[IndexedFill]:
    """Get recent fills for a user.

    Args:
        db: Database session
        user_addr: User wallet address
        symbol: Optional symbol filter
        limit: Max results

    Returns:
        List of IndexedFill objects
    """
    query = db.query(IndexedFill).filter_by(user_address=user_addr.lower())
    if symbol:
        query = query.filter_by(symbol=symbol.upper())
    return query.order_by(IndexedFill.ts.desc()).limit(limit).all()
