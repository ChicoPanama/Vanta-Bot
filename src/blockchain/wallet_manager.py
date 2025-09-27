from cryptography.fernet import Fernet
from src.config.settings import config
from src.blockchain.base_client import base_client
import logging

logger = logging.getLogger(__name__)

class WalletManager:
    def __init__(self):
        self.cipher_suite = Fernet(config.ENCRYPTION_KEY.encode())
        
    def create_wallet(self):
        """Create new wallet and return encrypted private key"""
        wallet = base_client.create_wallet()
        
        encrypted_private_key = self.encrypt_private_key(wallet['private_key'])
        
        return {
            'address': wallet['address'],
            'encrypted_private_key': encrypted_private_key
        }
        
    def encrypt_private_key(self, private_key: str) -> str:
        """Encrypt private key for storage"""
        return self.cipher_suite.encrypt(private_key.encode()).decode()
        
    def decrypt_private_key(self, encrypted_private_key: str) -> str:
        """Decrypt private key for use"""
        return self.cipher_suite.decrypt(encrypted_private_key.encode()).decode()
        
    def get_wallet_info(self, address: str):
        """Get wallet balance information"""
        eth_balance = base_client.get_balance(address)
        usdc_balance = base_client.get_usdc_balance(address)
        
        return {
            'address': address,
            'eth_balance': eth_balance,
            'usdc_balance': usdc_balance
        }

# Global instance
wallet_manager = WalletManager()
