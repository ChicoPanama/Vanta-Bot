from web3 import Web3
from eth_account import Account
from src.config.settings import config
import logging

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

# Use mock client for testing
base_client = MockBaseClient()
