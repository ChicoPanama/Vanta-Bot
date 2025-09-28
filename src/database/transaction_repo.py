"""Transaction repository for idempotency and tracking."""

import logging
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from src.database.models import SentTransaction

logger = logging.getLogger(__name__)


class TransactionRepository:
    """Repository for managing sent transactions and idempotency."""
    
    def __init__(self, db_session: Session):
        self.db = db_session

    def get_by_request_id(self, request_id: str) -> Optional[SentTransaction]:
        """Get transaction by request ID for idempotency check.
        
        Args:
            request_id: Unique request identifier
            
        Returns:
            SentTransaction if found, None otherwise
        """
        try:
            return self.db.query(SentTransaction).filter(
                SentTransaction.request_id == request_id
            ).first()
        except Exception as e:
            logger.error(f"Failed to get transaction by request ID {request_id}: {e}")
            return None

    def record_sent(self, request_id: str, tx_hash: str, wallet_id: str = None) -> SentTransaction:
        """Record a sent transaction.
        
        Args:
            request_id: Unique request identifier
            tx_hash: Transaction hash
            wallet_id: Wallet ID (optional)
            
        Returns:
            Created SentTransaction record
        """
        try:
            sent_tx = SentTransaction(
                request_id=request_id,
                tx_hash=tx_hash,
                wallet_id=wallet_id,
                status="PENDING"
            )
            
            self.db.add(sent_tx)
            self.db.commit()
            
            logger.info(f"Recorded sent transaction: {tx_hash} for request {request_id}")
            return sent_tx
            
        except Exception as e:
            logger.error(f"Failed to record sent transaction: {e}")
            self.db.rollback()
            raise

    def update_status(self, request_id: str, status: str, confirmed_at: datetime = None):
        """Update transaction status.
        
        Args:
            request_id: Request identifier
            status: New status (PENDING, CONFIRMED, FAILED)
            confirmed_at: Confirmation timestamp (optional)
        """
        try:
            sent_tx = self.get_by_request_id(request_id)
            if sent_tx:
                sent_tx.status = status
                if confirmed_at:
                    sent_tx.confirmed_at = confirmed_at
                
                self.db.commit()
                logger.info(f"Updated transaction {request_id} status to {status}")
            else:
                logger.warning(f"Transaction {request_id} not found for status update")
                
        except Exception as e:
            logger.error(f"Failed to update transaction status: {e}")
            self.db.rollback()
            raise

    def get_pending_transactions(self, limit: int = 100) -> list[SentTransaction]:
        """Get pending transactions for monitoring.
        
        Args:
            limit: Maximum number of transactions to return
            
        Returns:
            List of pending transactions
        """
        try:
            return self.db.query(SentTransaction).filter(
                SentTransaction.status == "PENDING"
            ).limit(limit).all()
        except Exception as e:
            logger.error(f"Failed to get pending transactions: {e}")
            return []

    def cleanup_old_transactions(self, days: int = 30):
        """Clean up old transaction records.
        
        Args:
            days: Number of days to keep records
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            deleted_count = self.db.query(SentTransaction).filter(
                SentTransaction.created_at < cutoff_date
            ).delete()
            
            self.db.commit()
            logger.info(f"Cleaned up {deleted_count} old transaction records")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old transactions: {e}")
            self.db.rollback()
            raise
