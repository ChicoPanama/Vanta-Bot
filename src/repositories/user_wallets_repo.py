"""User wallet binding repository (Phase 5)."""

from typing import Optional

from sqlalchemy.orm import Session
from web3 import Web3

from src.database.models import UserWallet


def bind_wallet(db: Session, tg_user_id: int, address: str) -> UserWallet:
    """Bind telegram user to wallet address.

    Args:
        db: Database session
        tg_user_id: Telegram user ID
        address: Ethereum address

    Returns:
        UserWallet record
    """
    addr = Web3.to_checksum_address(address)
    rec = db.query(UserWallet).filter_by(tg_user_id=tg_user_id).one_or_none()
    if rec:
        rec.address = addr
        db.add(rec)
        db.commit()
        db.refresh(rec)
        return rec

    rec = UserWallet(tg_user_id=tg_user_id, address=addr)
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def get_wallet(db: Session, tg_user_id: int) -> Optional[str]:
    """Get wallet address for telegram user.

    Args:
        db: Database session
        tg_user_id: Telegram user ID

    Returns:
        Ethereum address or None if not bound
    """
    rec = db.query(UserWallet).filter_by(tg_user_id=tg_user_id).one_or_none()
    return rec.address if rec else None
