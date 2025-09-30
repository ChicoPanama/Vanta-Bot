"""Repository for encrypted API credentials (Phase 1)."""

import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from src.database.models import ApiCredential

logger = logging.getLogger(__name__)


def upsert_api_secret(
    db: Session,
    user_id: int,
    provider: str,
    secret: dict[str, Any],
    meta: Optional[dict[str, Any]] = None,
) -> ApiCredential:
    """Store or update encrypted API secret.

    Args:
        db: Database session
        user_id: User ID
        provider: Provider name (e.g., "telegram", "exchange")
        secret: Secret data to encrypt (will be encrypted via EncryptedJSON)
        meta: Optional metadata to encrypt

    Returns:
        ApiCredential instance
    """
    exists = (
        db.query(ApiCredential)
        .filter_by(user_id=user_id, provider=provider)
        .one_or_none()
    )

    if exists:
        # Update existing credential
        exists.secret_enc = secret  # EncryptedJSON type handles encryption
        exists.meta_enc = meta or {}
        db.add(exists)
        logger.info(f"Updated API secret for user {user_id}, provider {provider}")
        return exists

    # Create new credential
    rec = ApiCredential(
        user_id=user_id,
        provider=provider,
        secret_enc=secret,
        meta_enc=meta or {},
    )
    db.add(rec)
    logger.info(f"Created API secret for user {user_id}, provider {provider}")
    return rec


def get_api_secret(
    db: Session, user_id: int, provider: str
) -> Optional[dict[str, Any]]:
    """Retrieve encrypted API secret.

    Args:
        db: Database session
        user_id: User ID
        provider: Provider name

    Returns:
        Decrypted secret dict or None if not found
    """
    rec = (
        db.query(ApiCredential)
        .filter_by(user_id=user_id, provider=provider)
        .one_or_none()
    )
    return rec.secret_enc if rec else None


def delete_api_secret(db: Session, user_id: int, provider: str) -> bool:
    """Delete API secret.

    Args:
        db: Database session
        user_id: User ID
        provider: Provider name

    Returns:
        True if deleted, False if not found
    """
    rec = (
        db.query(ApiCredential)
        .filter_by(user_id=user_id, provider=provider)
        .one_or_none()
    )

    if rec:
        db.delete(rec)
        logger.info(f"Deleted API secret for user {user_id}, provider {provider}")
        return True

    return False
