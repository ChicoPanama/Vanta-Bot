"""Transaction orchestrator with idempotency and persistence (Phase 2)."""

import json
import logging
import time
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy.orm import Session
from web3 import Web3
from web3.exceptions import TransactionNotFound

from src.blockchain.signers.factory import get_signer
from src.database.models import TxIntent, TxReceipt, TxSend

from .builder import TxBuilder
from .gas_policy import GasPolicy

logger = logging.getLogger(__name__)


class TxOrchestrator:
    """Orchestrates transaction lifecycle with idempotency and persistence."""

    def __init__(
        self,
        web3: Web3,
        db: Session,
        gas_policy: Optional[GasPolicy] = None,
        rbf_attempts: int = 2,
        rbf_bump_multiplier: float = 1.15,
    ):
        """Initialize transaction orchestrator.

        Args:
            web3: Web3 instance
            db: Database session
            gas_policy: Gas policy (default if None)
            rbf_attempts: Number of RBF retry attempts
            rbf_bump_multiplier: Fee bump multiplier for RBF
        """
        self.web3 = web3
        self.db = db
        self.signer = get_signer(web3)
        self.builder = TxBuilder(web3, web3.eth.chain_id, gas_policy)
        self.gas_policy = gas_policy or GasPolicy()
        self.rbf_attempts = rbf_attempts
        self.rbf_bump_multiplier = rbf_bump_multiplier

    def _get_or_create_intent(self, intent_key: str, metadata: dict) -> TxIntent:
        """Get or create transaction intent.

        Args:
            intent_key: Idempotency key
            metadata: Intent metadata

        Returns:
            TxIntent instance
        """
        intent = self.db.query(TxIntent).filter_by(intent_key=intent_key).one_or_none()

        if intent:
            logger.info(f"Found existing intent: {intent_key}")
            return intent

        # Create new intent
        intent = TxIntent(
            intent_key=intent_key,
            status="CREATED",
            intent_metadata=json.dumps(metadata),
        )
        self.db.add(intent)
        self.db.commit()
        self.db.refresh(intent)

        logger.info(f"Created new intent: {intent_key}")
        return intent

    def execute(
        self,
        intent_key: str,
        to: str,
        data: bytes,
        value: int = 0,
        gas_limit_hint: Optional[int] = None,
        confirmations: int = 2,
        metadata: Optional[dict] = None,
    ) -> str:
        """Execute transaction with idempotency and RBF retries.

        Args:
            intent_key: Idempotency key (e.g., "open:USER:UUID")
            to: Recipient address
            data: Transaction data
            value: ETH value in wei
            gas_limit_hint: Optional gas limit
            confirmations: Number of confirmations to wait for
            metadata: Optional metadata to store

        Returns:
            Transaction hash

        Raises:
            RuntimeError: If transaction fails
        """
        # Check for existing completed intent
        intent = self._get_or_create_intent(intent_key, metadata or {"to": to})

        if intent.status in ("SENT", "MINED"):
            # Return existing tx hash
            existing_send = (
                self.db.query(TxSend)
                .filter_by(intent_id=intent.id)
                .order_by(TxSend.id.desc())
                .first()
            )
            if existing_send:
                logger.info(f"Intent already {intent.status}, returning existing tx: {existing_send.tx_hash}")
                return existing_send.tx_hash

        # Build transaction
        from_addr = self.signer.address
        tx_params = self.builder.build_tx_params(
            to=to,
            data=data,
            from_addr=from_addr,
            value=value,
            gas_limit_hint=gas_limit_hint,
        )

        intent.status = "BUILT"
        self.db.add(intent)
        self.db.commit()

        # Get nonce synchronously (simplified for Phase 2)
        nonce = self.web3.eth.get_transaction_count(from_addr, "pending")
        tx_params["nonce"] = nonce

        # Sign transaction
        raw_tx = self.signer.sign_tx(tx_params)

        # Send initial transaction
        tx_hash = self.web3.eth.send_raw_transaction(raw_tx).hex()

        # Persist send record
        send = TxSend(
            intent_id=intent.id,
            chain_id=self.web3.eth.chain_id,
            nonce=nonce,
            max_fee_per_gas=int(tx_params["maxFeePerGas"]),
            max_priority_fee_per_gas=int(tx_params["maxPriorityFeePerGas"]),
            gas_limit=int(tx_params["gas"]),
            raw_tx=b"",  # Optionally store; omitted for size
            tx_hash=tx_hash,
            sent_at=datetime.utcnow(),
        )
        self.db.add(send)
        intent.status = "SENT"
        self.db.add(intent)
        self.db.commit()

        logger.info(f"Sent transaction: {tx_hash}")

        # Wait for confirmation with RBF retries
        last_hash = tx_hash
        for attempt in range(self.rbf_attempts):
            try:
                # Try to get receipt (shorter timeout for initial attempts)
                timeout = 5 if attempt < self.rbf_attempts - 1 else 30
                receipt = self._wait_for_receipt(last_hash, timeout=timeout)
                if receipt:
                    # Success - persist receipt
                    self._persist_receipt(receipt, intent)
                    return last_hash
            except TimeoutError:
                if attempt < self.rbf_attempts - 1:
                    # Bump fees and replace
                    logger.warning(f"Transaction stuck, attempting RBF (attempt {attempt + 1})")
                    last_hash = self._replace_transaction(
                        tx_params, nonce, send, intent
                    )
                else:
                    # Final timeout - mark as failed
                    intent.status = "FAILED"
                    self.db.add(intent)
                    self.db.commit()
                    raise RuntimeError(f"Transaction timed out after {self.rbf_attempts} attempts: {last_hash}")

        return last_hash

    def _wait_for_receipt(self, tx_hash: str, timeout: int = 60):
        """Wait for transaction receipt.

        Args:
            tx_hash: Transaction hash
            timeout: Timeout in seconds

        Returns:
            Receipt or None if timeout

        Raises:
            TimeoutError: If transaction doesn't mine within timeout
        """
        start = time.time()
        poll_interval = 1  # Poll every second
        while time.time() - start < timeout:
            try:
                receipt = self.web3.eth.get_transaction_receipt(tx_hash)
                return receipt
            except TransactionNotFound:
                time.sleep(poll_interval)

        raise TimeoutError(f"Transaction {tx_hash} not mined within {timeout}s")

    def _replace_transaction(
        self, tx_params: dict, nonce: int, original_send: TxSend, intent: TxIntent
    ) -> str:
        """Replace transaction with higher fees (RBF).

        Args:
            tx_params: Original transaction parameters
            nonce: Nonce to reuse
            original_send: Original send record
            intent: Intent record

        Returns:
            New transaction hash
        """
        # Bump fees
        new_max_fee = int(tx_params["maxFeePerGas"] * self.rbf_bump_multiplier)
        new_priority = int(tx_params["maxPriorityFeePerGas"] * self.rbf_bump_multiplier)

        # Cap fees
        max_fee_cap = int(self.gas_policy.max_fee_cap_gwei * 1e9)
        new_max_fee = min(new_max_fee, max_fee_cap)

        # Build replacement tx
        tx_params["maxFeePerGas"] = new_max_fee
        tx_params["maxPriorityFeePerGas"] = new_priority
        tx_params["nonce"] = nonce

        # Sign and send
        raw_tx = self.signer.sign_tx(tx_params)
        new_hash = self.web3.eth.send_raw_transaction(raw_tx).hex()

        # Update original send record
        original_send.replaced_by = new_hash
        self.db.add(original_send)

        # Create new send record
        new_send = TxSend(
            intent_id=intent.id,
            chain_id=self.web3.eth.chain_id,
            nonce=nonce,
            max_fee_per_gas=new_max_fee,
            max_priority_fee_per_gas=new_priority,
            gas_limit=int(tx_params["gas"]),
            raw_tx=b"",
            tx_hash=new_hash,
            sent_at=datetime.utcnow(),
        )
        self.db.add(new_send)
        intent.status = "REPLACED"
        self.db.add(intent)
        self.db.commit()

        logger.info(f"Replaced tx {original_send.tx_hash} with {new_hash} (fees bumped)")
        return new_hash

    def _persist_receipt(self, receipt, intent: TxIntent):
        """Persist transaction receipt.

        Args:
            receipt: Web3 transaction receipt
            intent: Intent record
        """
        tx_receipt = TxReceipt(
            tx_hash=receipt.transactionHash.hex(),
            status=receipt.status,
            block_number=receipt.blockNumber,
            gas_used=receipt.gasUsed,
            effective_gas_price=receipt.effectiveGasPrice,
            mined_at=datetime.utcnow(),
        )
        self.db.add(tx_receipt)

        intent.status = "MINED" if receipt.status == 1 else "FAILED"
        self.db.add(intent)
        self.db.commit()

        logger.info(
            f"Receipt persisted: {receipt.transactionHash.hex()} - status={intent.status}"
        )

    def reconcile_nonce(self, address: Optional[str] = None):
        """Reconcile nonce with on-chain state (Phase 2 helper).

        Args:
            address: Address to reconcile (defaults to signer address)

        Returns:
            Current on-chain nonce
        """
        addr = address or self.signer.address
        onchain_nonce = self.web3.eth.get_transaction_count(addr, "pending")
        logger.info(f"Reconciled nonce for {addr}: {onchain_nonce}")
        return onchain_nonce
