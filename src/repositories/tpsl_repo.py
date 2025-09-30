"""TP/SL repository (Phase 7)."""

from sqlalchemy.orm import Session

from src.database.models import TPSL


def add_tpsl(
    db: Session,
    tg_user_id: int,
    symbol: str,
    is_long: bool,
    tp: float | None,
    sl: float | None,
) -> TPSL:
    """Add TP/SL order."""
    rec = TPSL(
        tg_user_id=tg_user_id,
        symbol=symbol,
        is_long=is_long,
        take_profit_price=tp,
        stop_loss_price=sl,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def list_tpsl(db: Session, tg_user_id: int | None = None) -> list[TPSL]:
    """List active TP/SL orders."""
    query = db.query(TPSL).filter_by(active=True)
    if tg_user_id is not None:
        query = query.filter_by(tg_user_id=tg_user_id)
    return query.all()


def deactivate_tpsl(db: Session, tpsl_id: int):
    """Deactivate TP/SL order."""
    rec = db.query(TPSL).filter_by(id=tpsl_id).one_or_none()
    if rec:
        rec.active = False
        db.commit()
