import logging
from decimal import Decimal
from typing import Optional

import redis
from eth_account import Account
from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider

from src.config.settings import settings

logger = logging.getLogger(__name__)


class BaseClient:
    """Production Base client with real Web3 connection"""

    def __init__(self):
        """Initialize Base client with Web3 connection"""
        if settings.BASE_RPC_URL == "memory":
            # Test mode - use mock provider
            self.w3 = Web3(EthereumTesterProvider())
        else:
            # Production mode - use real RPC
            self.w3 = Web3(Web3.HTTPProvider(settings.BASE_RPC_URL))

        if not self.w3.is_connected():
            raise RuntimeError(
                f"Failed to connect to Base network: {settings.BASE_RPC_URL}"
            )

        logger.info(f"Base client initialized with {settings.BASE_RPC_URL}")

    def get_balance(self, address: str) -> float:
        """Get ETH balance for address"""
        try:
            # FIX: Implement real balance fetching instead of mock
            # REASON: Production code was returning mock data
            balance_wei = self.w3.eth.get_balance(address)
            balance_eth = self.w3.from_wei(balance_wei, "ether")
            return float(balance_eth)
        except Exception as e:
            logger.error(f"Error getting ETH balance for {address}: {e}")
            raise

    def get_usdc_balance(self, address: str) -> float:
        """Get USDC balance for address"""
        try:
            # FIX: Implement real USDC balance fetching
            # REASON: Production code was returning mock data
            # USDC is ERC-20 token with 6 decimals
            if getattr(self, "_using_memory", False):
                return 0.0

            usdc_contract_address = settings.USDC_CONTRACT
            if not usdc_contract_address:
                logger.warning("USDC contract address not configured")
                return 0.0

            # Simple ERC-20 balanceOf call
            balance_of_abi = [
                {
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "balance", "type": "uint256"}],
                    "type": "function",
                }
            ]

            contract = self.w3.eth.contract(
                address=self.w3.to_checksum_address(usdc_contract_address),
                abi=balance_of_abi,
            )

            balance_raw = contract.functions.balanceOf(
                self.w3.to_checksum_address(address)
            ).call()
            # USDC has 6 decimals
            balance_usdc = balance_raw / Decimal("1000000")
            return float(balance_usdc)

        except Exception as e:
            logger.error(f"Error getting USDC balance for {address}: {e}")
            raise

    def __init__(self, signer=None):
        """Initialize BaseClient with optional signer.

        Args:
            signer: Signer instance for transaction signing
        """
        try:
            # FIX: Replace MockBaseClient with real Web3 client in prod path
            # REASON: Mock client was wired for production - critical security issue
            # REVIEW: Line ? from code review - Mock client wired for production

            rpc_url = settings.BASE_RPC_URL
            self._using_memory = rpc_url.lower() == "memory"

            if self._using_memory:
                provider = EthereumTesterProvider()
                self.w3 = Web3(provider)
                self.chain_id = self.w3.eth.chain_id
                logger.info(
                    "Initialized Base client with in-memory Ethereum tester provider"
                )
            else:
                # Add request timeout to avoid indefinite hangs on RPC calls
                provider = Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 15})
                self.w3 = Web3(provider)
                self.chain_id = settings.BASE_CHAIN_ID

                if not self.w3.is_connected():
                    logger.error(f"Failed to connect to Base RPC: {rpc_url}")
                    raise ConnectionError("Cannot connect to Base network")

                network_chain_id = self.w3.eth.chain_id
                if network_chain_id != self.chain_id:
                    logger.error(
                        f"Chain ID mismatch: expected {self.chain_id}, got {network_chain_id}"
                    )
                    raise ValueError(
                        f"Chain ID mismatch: expected {self.chain_id}, got {network_chain_id}"
                    )

                logger.info(f"Connected to Base network (Chain ID: {network_chain_id})")

            # Initialize Redis for nonce management
            try:
                self.redis = redis.from_url(settings.REDIS_URL)
                self.redis.ping()  # Test connection
                logger.info("Connected to Redis for nonce management")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                self.redis = None

            # Initialize database session manager
            from src.database.session import get_session_manager

            self.db_manager = get_session_manager()

            # Store signer
            self.signer = signer

        except Exception as e:
            logger.error(f"Failed to initialize Base client: {e}")
            raise

    async def submit(self, tx_params: dict, *, request_id: str) -> str:
        """Submit transaction using injected signer.

        Args:
            tx_params: Transaction parameters
            request_id: Unique request identifier for idempotency

        Returns:
            Transaction hash
        """
        try:
            if not self.signer:
                raise ValueError("No signer configured - cannot send transactions")

            # Import here to avoid circular imports
            from src.blockchain.tx.builder import TxBuilder
            from src.blockchain.tx.gas_policy import GasPolicy
            from src.blockchain.tx.nonce_manager import NonceManager
            from src.database.transaction_repo import (
                TransactionRepository,
                calculate_payload_hash,
            )

            # Calculate payload hash for idempotency
            payload_hash = calculate_payload_hash(tx_params)

            # Check idempotency using database session
            async with self.db_manager.get_session() as session:
                repo = TransactionRepository(session)

                # Check if transaction already exists
                existing = await repo.get_by_request_id(request_id)
                if existing:
                    logger.info(
                        f"Transaction already exists: {request_id} -> {existing.tx_hash}"
                    )
                    return existing.tx_hash

                # Initialize components
                nonce_manager = NonceManager(self.redis, self.w3)
                gas_policy = GasPolicy()
                tx_builder = TxBuilder(self.w3, self.chain_id)

                # Reserve nonce
                async with nonce_manager.reserve(self.signer.address) as nonce:
                    # Get gas quote
                    max_fee, max_priority = gas_policy.quote(self.w3)

                    # Estimate gas
                    gas = tx_builder.estimate_gas(tx_params)

                    # Build transaction
                    tx = tx_builder.build(
                        from_addr=self.signer.address,
                        to=tx_params.get("to"),
                        data=tx_params.get("data", b""),
                        value=tx_params.get("value", 0),
                        gas=gas,
                        nonce=nonce,
                        max_fee=max_fee,
                        max_priority=max_priority,
                    )

                    # Sign and send using signer
                    tx_hash = await self.signer.sign_and_send(tx)

                    # Record transaction for idempotency
                    await repo.record_if_new(request_id, tx_hash, payload_hash)
                    await session.commit()

                    logger.info(f"Transaction submitted: {tx_hash}")
                    return tx_hash

        except Exception as e:
            logger.error(f"Error submitting transaction: {e}")
            raise

    def send_transaction(
        self, wallet_id: str, tx_params: dict, request_id: str, private_key: str = None
    ) -> str:
        """Legacy method for backward compatibility.

        DEPRECATED: Use submit() method with injected signer instead.
        """
        logger.warning(
            "send_transaction is deprecated - use submit() with injected signer"
        )

        if not self.signer:
            raise NotImplementedError(
                "No signer configured - use submit() method with injected signer"
            )

        # Convert to new interface - use new_event_loop for thread safety
        import asyncio

        def run_in_thread():
            # Create a new event loop in a separate thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    self.submit(tx_params, request_id=request_id)
                )
            finally:
                loop.close()

        # Run in a separate thread to avoid event loop conflicts
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_thread)
            return future.result()

    def create_wallet(self) -> dict[str, str]:
        """Create new wallet"""
        try:
            # FIX: Implement real wallet creation instead of mock
            # REASON: Production code was using mock wallet creation
            account = Account.create()
            return {"address": account.address, "private_key": account.key.hex()}
        except Exception as e:
            logger.error(f"Error creating wallet: {e}")
            raise

    def get_transaction_count(self, address: str) -> int:
        """Get transaction count (nonce) for address"""
        try:
            # FIX: Implement real nonce fetching instead of mock
            # REASON: Production code was returning mock nonce
            return self.w3.eth.get_transaction_count(address)
        except Exception as e:
            logger.error(f"Error getting transaction count for {address}: {e}")
            raise


_CLIENT: Optional[BaseClient] = None


def get_base_client() -> BaseClient:
    """Return a singleton BaseClient wired to the configured RPC."""
    global _CLIENT
    if _CLIENT is None:
        # Create signer based on configuration
        from .signer_factory import create_signer

        # Create a proper Web3 instance with provider
        rpc_url = settings.BASE_RPC_URL
        if rpc_url.lower() == "memory":
            provider = EthereumTesterProvider()
        else:
            provider = Web3.HTTPProvider(rpc_url)
        w3 = Web3(provider)
        signer = create_signer(w3)
        _CLIENT = BaseClient(signer)
    return _CLIENT


class _BaseClientProxy:
    def __getattr__(self, item):  # pragma: no cover - thin proxy
        return getattr(get_base_client(), item)


base_client = _BaseClientProxy()
