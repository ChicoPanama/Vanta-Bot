"""Transaction sender with retries and idempotency."""

import random
import time
import logging
from typing import Optional, Dict, Any
from web3 import Web3

logger = logging.getLogger(__name__)


class TxSender:
    """Sends transactions with retry logic and idempotency."""
    
    def __init__(self, web3_client: Web3, tx_repo, private_rpc: Optional[str] = None):
        self.web3 = web3_client
        self.tx_repo = tx_repo
        self.private_rpc = private_rpc

    def send_with_retry(self, 
                       raw_tx: bytes, 
                       request_id: str, 
                       retries: int = 3, 
                       base_sleep: float = 0.5) -> str:
        """Send transaction with retry logic and idempotency.
        
        Args:
            raw_tx: Raw signed transaction bytes
            request_id: Unique request identifier for idempotency
            retries: Number of retry attempts
            base_sleep: Base sleep time between retries
            
        Returns:
            Transaction hash
            
        Raises:
            Exception: If all retries fail
        """
        # Check if transaction already sent
        existing_tx = self.tx_repo.get_by_request_id(request_id)
        if existing_tx:
            logger.info(f"Transaction already sent for request {request_id}: {existing_tx.tx_hash}")
            return existing_tx.tx_hash

        last_exception = None
        
        for attempt in range(retries + 1):
            try:
                # Send transaction
                if self.private_rpc:
                    # Use private RPC endpoint for MEV protection
                    tx_hash = self._send_private(raw_tx)
                else:
                    # Use public RPC
                    tx_hash = self.web3.eth.send_raw_transaction(raw_tx)
                
                # Record successful send
                self.tx_repo.record_sent(request_id, tx_hash.hex())
                
                logger.info(f"Transaction sent successfully: {tx_hash.hex()}")
                return tx_hash.hex()
                
            except Exception as e:
                last_exception = e
                logger.warning(f"Transaction send attempt {attempt + 1} failed: {e}")
                
                if attempt < retries:
                    # Exponential backoff with jitter
                    sleep_time = base_sleep * (2 ** attempt) + random.random() * 0.2
                    logger.debug(f"Retrying in {sleep_time:.2f} seconds...")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"All retry attempts failed for request {request_id}")
        
        # All retries failed
        raise last_exception or Exception("Transaction send failed")

    def _send_private(self, raw_tx: bytes) -> str:
        """Send transaction via private RPC endpoint.
        
        Args:
            raw_tx: Raw signed transaction bytes
            
        Returns:
            Transaction hash
        """
        # This would integrate with private mempool services like Flashbots
        # For now, fall back to public RPC
        logger.info("Private RPC not implemented, using public RPC")
        return self.web3.eth.send_raw_transaction(raw_tx)

    def bump_and_retry(self, 
                     original_tx: Dict[str, Any], 
                     request_id: str, 
                     gas_policy) -> str:
        """Bump gas fees and retry failed transaction.
        
        Args:
            original_tx: Original transaction parameters
            request_id: Request identifier
            gas_policy: Gas policy instance for fee bumping
            
        Returns:
            New transaction hash
        """
        try:
            # Bump the max fee
            bumped_max_fee = gas_policy.bump_fee(original_tx["maxFeePerGas"])
            
            # Create new transaction with bumped fees
            new_tx = original_tx.copy()
            new_tx["maxFeePerGas"] = bumped_max_fee
            
            # Sign and send new transaction
            # Note: This would need the original private key
            # For now, this is a placeholder for the retry logic
            logger.info(f"Bumped fees for retry: {bumped_max_fee}")
            
            # This would need to be implemented with proper key management
            raise NotImplementedError("Fee bumping requires private key access")
            
        except Exception as e:
            logger.error(f"Failed to bump and retry transaction: {e}")
            raise
