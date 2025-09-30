"""Signals repository for Phase 6 automation."""

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from src.database.models import Execution, Signal


def upsert_signal(
    db: Session, *, source: str, signal_id: str, intent_key: str, payload: dict
) -> Signal:
    """Create or retrieve signal by intent_key.

    Args:
        db: Database session
        source: Signal source (e.g., "webhook:tradingview")
        signal_id: Provider's signal ID
        intent_key: Unique intent key for idempotency
        payload: Signal payload dict

    Returns:
        Signal record
    """
    sig = db.query(Signal).filter_by(intent_key=intent_key).one_or_none()
    if sig:
        return sig

    sig = Signal(
        source=source,
        signal_id=signal_id,
        intent_key=intent_key,
        tg_user_id=payload["tg_user_id"],
        symbol=payload["symbol"],
        side=payload["side"],
        collateral_usdc=float(payload.get("collateral_usdc", 0)),
        leverage_x=int(payload.get("leverage_x", 2)),
        reduce_usdc=float(payload.get("reduce_usdc", 0)),
        slippage_pct=float(payload.get("slippage_pct", 0.5)),
        meta=str(payload.get("meta", {})),
    )
    db.add(sig)
    db.commit()
    db.refresh(sig)
    return sig


def create_execution(
    db: Session, intent_key: str, status: str = "QUEUED", reason: Optional[str] = None
) -> Execution:
    """Create execution record.

    Args:
        db: Database session
        intent_key: Intent key linking to signal
        status: Execution status
        reason: Optional reason/error message

    Returns:
        Execution record
    """
    exc = db.query(Execution).filter_by(intent_key=intent_key).one_or_none()
    if exc:
        return exc

    exc = Execution(intent_key=intent_key, status=status, reason=reason)
    db.add(exc)
    db.commit()
    db.refresh(exc)
    return exc


def update_execution(
    db: Session,
    intent_key: str,
    *,
    status: str,
    reason: Optional[str] = None,
    tx_hash: Optional[str] = None,
) -> Execution:
    """Update execution status.

    Args:
        db: Database session
        intent_key: Intent key
        status: New status
        reason: Optional reason/error
        tx_hash: Optional transaction hash

    Returns:
        Updated Execution record
    """
    exc = db.query(Execution).filter_by(intent_key=intent_key).one_or_none()
    if not exc:
        exc = create_execution(db, intent_key, status=status, reason=reason)

    exc.status = status
    exc.reason = reason
    exc.tx_hash = tx_hash
    exc.updated_at = datetime.utcnow()

    db.add(exc)
    db.commit()
    db.refresh(exc)
    return exc
