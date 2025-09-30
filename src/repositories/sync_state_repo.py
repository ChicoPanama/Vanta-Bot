"""Sync state repository for indexer progress tracking (Phase 4)."""

from datetime import datetime

from sqlalchemy.orm import Session

from src.database.models import SyncState


def get_block(db: Session, name: str) -> int:
    """Get last synced block number for an indexer.

    Args:
        db: Database session
        name: Indexer name (e.g., "avantis_indexer")

    Returns:
        Last block number, or 0 if not found
    """
    state = db.query(SyncState).filter_by(name=name).one_or_none()
    return state.last_block if state else 0


def set_block(db: Session, name: str, block: int) -> None:
    """Set last synced block number for an indexer.

    Args:
        db: Database session
        name: Indexer name
        block: Block number to store
    """
    state = db.query(SyncState).filter_by(name=name).one_or_none()
    if not state:
        state = SyncState(name=name, last_block=block)

    state.last_block = block
    state.updated_at = datetime.utcnow()

    db.add(state)
    db.commit()
