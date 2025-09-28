from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider
from eth_account import Account
from src.config.settings import settings
import logging
from typing import Dict, Optional
from decimal import Decimal
import redis

logger = logging.getLogger(__name__)


class BaseClient:
    """Production Base client with real Web3 connection"""
    
    def __init__(self):
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
                logger.info("Initialized Base client with in-memory Ethereum tester provider")
            else:
                provider = Web3.HTTPProvider(rpc_url)
                self.w3 = Web3(provider)
                self.chain_id = settings.BASE_CHAIN_ID

                if not self.w3.is_connected():
                    logger.error(f"Failed to connect to Base RPC: {rpc_url}")
                    raise ConnectionError("Cannot connect to Base network")

                network_chain_id = self.w3.eth.chain_id
                if network_chain_id != self.chain_id:
                    logger.error(f"Chain ID mismatch: expected {self.chain_id}, got {network_chain_id}")
                    raise ValueError(f"Chain ID mismatch: expected {self.chain_id}, got {network_chain_id}")

                logger.info(f"Connected to Base network (Chain ID: {network_chain_id})")
            
            # Initialize Redis for nonce management
            try:
                self.redis = redis.from_url(settings.REDIS_URL)
                self.redis.ping()  # Test connection
                logger.info("Connected to Redis for nonce management")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                self.redis = None
            
            # Initialize database connection (placeholder)
            self.db = None  # This would be injected in a real implementation
            
        except Exception as e:
            logger.error(f"Failed to initialize Base client: {e}")
            raise
        
    def get_balance(self, address: str) -> float:
        """Get ETH balance for address"""
        try:
            # FIX: Implement real balance fetching instead of mock
            # REASON: Production code was returning mock data
            balance_wei = self.w3.eth.get_balance(address)
            balance_eth = self.w3.from_wei(balance_wei, 'ether')
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
            balance_of_abi = [{
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            }]
            
            contract = self.w3.eth.contract(
                address=self.w3.to_checksum_address(usdc_contract_address),
                abi=balance_of_abi
            )
            
            balance_raw = contract.functions.balanceOf(address).call()
            # USDC has 6 decimals
            balance_usdc = balance_raw / Decimal('1000000')
            return float(balance_usdc)
            
        except Exception as e:
            logger.error(f"Error getting USDC balance for {address}: {e}")
            raise
        
    def send_transaction(self, 
                        wallet_id: str, 
                        tx_params: dict, 
                        request_id: str,
                        private_key: str = None) -> str:
        """Send transaction using the new pipeline with envelope encryption.
        
        Args:
            wallet_id: Wallet identifier
            tx_params: Transaction parameters
            request_id: Unique request identifier for idempotency
            private_key: Private key (if not using envelope encryption)
            
        Returns:
            Transaction hash
        """
        try:
            # Import here to avoid circular imports
            from src.config.settings import settings
            from src.blockchain.tx.nonce_manager import NonceManager
            from src.blockchain.tx.gas_policy import GasPolicy
            from src.blockchain.tx.builder import TxBuilder
            from src.blockchain.tx.sender import TxSender
            from src.database.transaction_repo import TransactionRepository
            from src.middleware.circuit_breakers import circuit_breaker_manager
            
            # Initialize components
            nonce_manager = NonceManager(self.redis, self.w3)
            gas_policy = GasPolicy()
            tx_builder = TxBuilder(self.w3, self.chain_id)
            tx_sender = TxSender(self.w3, TransactionRepository(self.db))
            
            # Get private key
            if not private_key:
                # This would need to be implemented with proper wallet access
                raise NotImplementedError("Private key access not implemented")
            
            # Get sender address
            from_addr = self.w3.eth.account.from_key(bytes.fromhex(private_key)).address
            
            # Reserve nonce
            with nonce_manager.reserve(from_addr) as nonce:
                # Get gas quote
                max_fee, max_priority = gas_policy.quote(self.w3)
                
                # Estimate gas
                gas = tx_builder.estimate_gas(tx_params)
                
                # Build transaction
                tx = tx_builder.build(
                    from_addr=from_addr,
                    to=tx_params.get("to"),
                    data=tx_params.get("data", b""),
                    value=tx_params.get("value", 0),
                    gas=gas,
                    nonce=nonce,
                    max_fee=max_fee,
                    max_priority=max_priority
                )
                
                # Sign transaction
                raw_tx = tx_builder.sign(tx, private_key)
                
                # Send with retry logic
                tx_hash = tx_sender.send_with_retry(raw_tx, request_id)
                
                logger.info(f"Transaction sent: {tx_hash}")
                return tx_hash
                
        except Exception as e:
            logger.error(f"Error sending transaction: {e}")
            raise
        
    def create_wallet(self) -> Dict[str, str]:
        """Create new wallet"""
        try:
            # FIX: Implement real wallet creation instead of mock
            # REASON: Production code was using mock wallet creation
            account = Account.create()
            return {
                'address': account.address,
                'private_key': account.key.hex()
            }
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
        _CLIENT = BaseClient()
    return _CLIENT


class _BaseClientProxy:
    def __getattr__(self, item):  # pragma: no cover - thin proxy
        return getattr(get_base_client(), item)


base_client = _BaseClientProxy()
