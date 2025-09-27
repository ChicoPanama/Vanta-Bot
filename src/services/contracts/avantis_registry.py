"""
Avantis Contract Registry Service
Resolves contract addresses dynamically from the Trading Proxy
"""

import logging
from typing import Optional
from web3 import Web3
from web3.contract import Contract

logger = logging.getLogger(__name__)


class AvantisRegistry:
    """Service to resolve Avantis contract addresses dynamically"""
    
    def __init__(self, w3: Web3, trading_contract_address: str):
        self.w3 = w3
        self.trading_contract_address = trading_contract_address
        self._vault_address: Optional[str] = None
        
        # Candidate ABIs for vault resolution
        self.candidate_abis = [
            {"type": "function", "name": "vault", "inputs": [], "outputs": [{"type": "address"}], "stateMutability": "view"},
            {"type": "function", "name": "getVault", "inputs": [], "outputs": [{"type": "address"}], "stateMutability": "view"},
            {"type": "function", "name": "usdcVault", "inputs": [], "outputs": [{"type": "address"}], "stateMutability": "view"},
            {"type": "function", "name": "USDC_VAULT", "inputs": [], "outputs": [{"type": "address"}], "stateMutability": "view"},
            {"type": "function", "name": "getUSDCVault", "inputs": [], "outputs": [{"type": "address"}], "stateMutability": "view"},
            {"type": "function", "name": "vaultAddress", "inputs": [], "outputs": [{"type": "address"}], "stateMutability": "view"},
            {"type": "function", "name": "getVaultAddress", "inputs": [], "outputs": [{"type": "address"}], "stateMutability": "view"},
            {"type": "function", "name": "collateralVault", "inputs": [], "outputs": [{"type": "address"}], "stateMutability": "view"},
            {"type": "function", "name": "getCollateralVault", "inputs": [], "outputs": [{"type": "address"}], "stateMutability": "view"},
            {"type": "function", "name": "treasury", "inputs": [], "outputs": [{"type": "address"}], "stateMutability": "view"},
            {"type": "function", "name": "getTreasury", "inputs": [], "outputs": [{"type": "address"}], "stateMutability": "view"},
            {"type": "function", "name": "usdc", "inputs": [], "outputs": [{"type": "address"}], "stateMutability": "view"},
            {"type": "function", "name": "USDC", "inputs": [], "outputs": [{"type": "address"}], "stateMutability": "view"},
            {"type": "function", "name": "collateral", "inputs": [], "outputs": [{"type": "address"}], "stateMutability": "view"},
            {"type": "function", "name": "getCollateral", "inputs": [], "outputs": [{"type": "address"}], "stateMutability": "view"},
        ]
    
    async def resolve_vault_address(self) -> Optional[str]:
        """
        Resolve the vault contract address from the Trading Proxy
        Tries multiple function selectors in order of preference
        """
        if self._vault_address:
            return self._vault_address
            
        logger.info(f"🔍 Resolving vault address from Trading Proxy: {self.trading_contract_address}")
        
        for abi in self.candidate_abis:
            try:
                # Create contract instance with current ABI
                contract = self.w3.eth.contract(
                    address=self.trading_contract_address,
                    abi=[abi]
                )
                
                # Get the function name from ABI
                function_name = abi["name"]
                
                # Call the function
                vault_address = contract.functions[function_name]().call()
                
                # Validate the address
                if vault_address and vault_address != "0x0000000000000000000000000000000000000000":
                    self._vault_address = vault_address
                    logger.info(f"✅ Resolved vault address: {vault_address} via {function_name}()")
                    return vault_address
                    
            except Exception as e:
                logger.debug(f"❌ Failed to resolve via {abi['name']}(): {e}")
                continue
        
        # If no function works, return None instead of raising an exception
        # This allows the bot to continue without the vault contract
        logger.warning("⚠️ Could not resolve vault address from Trading Proxy")
        logger.info("Bot will continue without vault contract (trading features will work)")
        return None
    
    def get_vault_address(self) -> Optional[str]:
        """Get cached vault address"""
        return self._vault_address
    
    def set_vault_address(self, address: str):
        """Set vault address (for testing or manual override)"""
        self._vault_address = address
        logger.info(f"🔧 Vault address set manually: {address}")
    
    async def get_contract_info(self) -> dict:
        """Get information about resolved contracts"""
        vault_address = self.get_vault_address()
        
        return {
            "trading_contract": self.trading_contract_address,
            "vault_contract": vault_address,
            "vault_resolved": vault_address is not None,
            "chain_id": self.w3.eth.chain_id,
            "network": "Base Mainnet" if self.w3.eth.chain_id == 8453 else f"Chain {self.w3.eth.chain_id}"
        }


# Global registry instance
_registry: Optional[AvantisRegistry] = None


def get_registry() -> Optional[AvantisRegistry]:
    """Get the global registry instance"""
    return _registry


def initialize_registry(w3: Web3, trading_contract_address: str) -> AvantisRegistry:
    """Initialize the global registry instance"""
    global _registry
    _registry = AvantisRegistry(w3, trading_contract_address)
    return _registry


async def resolve_avantis_vault() -> Optional[str]:
    """
    Convenience function to resolve vault address using global registry
    """
    if not _registry:
        raise Exception("Registry not initialized. Call initialize_registry() first.")
    
    return await _registry.resolve_vault_address()
