"""Transaction repository for idempotency and audit trail."""

import hashlib
import json
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from sqlalchemy.exc import IntegrityError

from .models import Transaction

logger = logging.getLogger(__name__)


class TransactionRepository:
    """Repository for transaction idempotency and audit trail."""
    
    def __init__(self, session: AsyncSession):
        """Initialize with database session."""
        self.session = session
    
    async def record_if_new(self, request_id: str, tx_hash: str, payload_hash: str) -> bool:
        """Record transaction if not already recorded.
        
        Args:
            request_id: Unique request identifier
            tx_hash: Transaction hash
            payload_hash: Hash of transaction payload for idempotency
            
        Returns:
            True if transaction was recorded, False if already exists
        """
        try:
            # Check if transaction already exists
            stmt = select(Transaction).where(
                Transaction.request_id == request_id,
                Transaction.payload_hash == payload_hash
            )
            result = await self.session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                logger.info(f"Transaction already exists: {request_id}")
                return False
            
            # Record new transaction
            transaction = Transaction(
                request_id=request_id,
                tx_hash=tx_hash,
                payload_hash=payload_hash
            )
            self.session.add(transaction)
            await self.session.flush()
            
            logger.info(f"Recorded new transaction: {request_id} -> {tx_hash}")
            return True
            
        except IntegrityError as e:
            # Handle unique constraint violation
            logger.warning(f"Transaction already exists (integrity error): {request_id}")
            await self.session.rollback()
            return False
        except Exception as e:
            logger.error(f"Failed to record transaction {request_id}: {e}")
            await self.session.rollback()
            raise
    
    async def get_by_request_id(self, request_id: str) -> Optional[Transaction]:
        """Get transaction by request ID."""
        try:
            stmt = select(Transaction).where(Transaction.request_id == request_id)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get transaction {request_id}: {e}")
            raise
    
    async def get_by_tx_hash(self, tx_hash: str) -> Optional[Transaction]:
        """Get transaction by transaction hash."""
        try:
            stmt = select(Transaction).where(Transaction.tx_hash == tx_hash)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get transaction by hash {tx_hash}: {e}")
            raise


def calculate_payload_hash(tx_params: dict) -> str:
    """Calculate hash of transaction payload for idempotency.
    
    Args:
        tx_params: Transaction parameters
        
    Returns:
        SHA256 hash as hex string
    """
    # Sort keys for consistent hashing
    payload_str = json.dumps(tx_params, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(payload_str.encode()).hexdigest()