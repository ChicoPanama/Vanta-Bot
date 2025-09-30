"""Risk policy repository (Phase 7)."""

from datetime import datetime

from sqlalchemy.orm import Session

from src.database.models import UserRiskPolicy

DEFAULTS = {
    "max_leverage_x": 20,
    "max_position_usd_1e6": 100_000_000,
    "daily_loss_limit_1e6": 0,
}


def get_or_create_policy(db: Session, tg_user_id: int) -> UserRiskPolicy:
    """Get or create risk policy for user."""
    rec = db.query(UserRiskPolicy).filter_by(tg_user_id=tg_user_id).one_or_none()
    if rec:
        return rec
    rec = UserRiskPolicy(tg_user_id=tg_user_id, **DEFAULTS)
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def update_policy(db: Session, tg_user_id: int, **fields) -> UserRiskPolicy:
    """Update risk policy fields."""
    rec = get_or_create_policy(db, tg_user_id)
    for k, v in fields.items():
        setattr(rec, k, v)
    rec.updated_at = datetime.utcnow()
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec
