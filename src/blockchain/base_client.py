from web3 import Web3
from eth_account import Account
from src.config.settings import config
import logging
from typing import Dict, Any, Optional
from decimal import Decimal

logger = logging.getLogger(__name__)

class MockBaseClient:
    """Mock Base client for testing without network connection"""
    def __init__(self):
        # Create a mock Web3 instance
        self.w3 = Web3()
        self.chain_id = config.BASE_CHAIN_ID
        
    def get_balance(self, address: str) -> float:
        """Mock get ETH balance"""
        return 1.0  # Mock balance
        
    def get_usdc_balance(self, address: str) -> float:
        """Mock get USDC balance"""
        return 1000.0  # Mock USDC balance
        
    def send_transaction(self, transaction: dict, private_key: str) -> str:
        """Mock send transaction"""
        return f"0x{'a' * 64}"  # Mock transaction hash
        
    def create_wallet(self) -> dict:
        """Mock create wallet"""
        account = Account.create()
        return {
            'address': account.address,
            'private_key': account.key.hex()
        }
        
    def get_transaction_count(self, address: str) -> int:
        """Mock get transaction count"""
        return 0


class BaseClient:
    """Production Base client with real Web3 connection"""
    
    def __init__(self):
        try:
            # FIX: Replace MockBaseClient with real Web3 client in prod path
            # REASON: Mock client was wired for production - critical security issue
            # REVIEW: Line ? from code review - Mock client wired for production
            
            self.w3 = Web3(Web3.HTTPProvider(config.BASE_RPC_URL))
            self.chain_id = config.BASE_CHAIN_ID
            
            # Verify connection
            if not self.w3.is_connected():
                logger.error(f"Failed to connect to Base RPC: {config.BASE_RPC_URL}")
                raise ConnectionError("Cannot connect to Base network")
            
            # Verify chain ID
            network_chain_id = self.w3.eth.chain_id
            if network_chain_id != self.chain_id:
                logger.error(f"Chain ID mismatch: expected {self.chain_id}, got {network_chain_id}")
                raise ValueError(f"Chain ID mismatch: expected {self.chain_id}, got {network_chain_id}")
            
            logger.info(f"Connected to Base network (Chain ID: {network_chain_id})")
            
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
            return 0.0
        
    def get_usdc_balance(self, address: str) -> float:
        """Get USDC balance for address"""
        try:
            # FIX: Implement real USDC balance fetching
            # REASON: Production code was returning mock data
            # USDC is ERC-20 token with 6 decimals
            usdc_contract_address = config.USDC_CONTRACT
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
            return 0.0
        
    def send_transaction(self, transaction: dict, private_key: str) -> str:
        """Send transaction to Base network"""
        try:
            # FIX: Implement real transaction sending instead of mock
            # REASON: Production code was returning mock transaction hash
            
            # Sign transaction
            signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key)
            
            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            logger.info(f"Transaction sent: {tx_hash.hex()}")
            return tx_hash.hex()
            
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
            return 0


# FIX: Use proper client based on environment instead of always mock
# REASON: Mock client was wired for production - critical security issue
# REVIEW: Line ? from code review - Mock client wired for production

def get_base_client():
    """Get appropriate Base client based on environment"""
    if config.is_production() or config.is_development():
        # Use real client for production and development
        return BaseClient()
    else:
        # Use mock client only for testing
        logger.warning("Using mock Base client - should only be used in testing")
        return MockBaseClient()

# Initialize client based on environment
base_client = get_base_client()
