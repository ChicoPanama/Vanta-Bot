"""
Address guard - prevents usage of deprecated contract addresses.

This module provides startup guards to ensure the application
never accidentally uses deprecated contract addresses.
"""

import json
import logging
from typing import Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


class AddressGuard:
    """Guards against usage of deprecated contract addresses."""
    
    def __init__(self, config_dir: str = "config/addresses"):
        """
        Initialize address guard.
        
        Args:
            config_dir: Directory containing address configuration files
        """
        self.config_dir = Path(config_dir)
        self.legacy_addresses = self._load_legacy_addresses()
        self.current_addresses = self._load_current_addresses()
        
        logger.info(f"Address guard initialized")
        logger.info(f"  Legacy addresses: {len(self.legacy_addresses)}")
        logger.info(f"  Current addresses: {len(self.current_addresses)}")
    
    def _load_legacy_addresses(self) -> Dict[str, Any]:
        """Load legacy address configurations."""
        legacy_addresses = {}
        
        for config_file in self.config_dir.glob("*.legacy.json"):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                
                # Extract all addresses from legacy config
                contracts = config.get("contracts", {})
                for contract_name, contract_info in contracts.items():
                    address = contract_info.get("address")
                    if address:
                        legacy_addresses[address.lower()] = {
                            "file": config_file.name,
                            "contract": contract_name,
                            "deprecated_at": config.get("deprecatedAt"),
                            "warning": config.get("warning"),
                            "replacement": config.get("replacement")
                        }
                
            except Exception as e:
                logger.warning(f"Failed to load legacy config {config_file}: {e}")
        
        return legacy_addresses
    
    def _load_current_addresses(self) -> Dict[str, Any]:
        """Load current address configurations."""
        current_addresses = {}
        
        for config_file in self.config_dir.glob("*.mainnet.json"):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                
                # Extract all addresses from current config
                contracts = config.get("contracts", {})
                for contract_name, contract_info in contracts.items():
                    address = contract_info.get("address")
                    if address:
                        current_addresses[address.lower()] = {
                            "file": config_file.name,
                            "contract": contract_name,
                            "network": config.get("network"),
                            "version": contract_info.get("version")
                        }
                
            except Exception as e:
                logger.warning(f"Failed to load current config {config_file}: {e}")
        
        return current_addresses
    
    def validate_address(self, address: str, context: str = "") -> None:
        """
        Validate that an address is not deprecated.
        
        Args:
            address: Contract address to validate
            context: Context information for error messages
        
        Raises:
            ValueError: If address is deprecated
        """
        normalized_address = address.lower()
        
        if normalized_address in self.legacy_addresses:
            legacy_info = self.legacy_addresses[normalized_address]
            
            error_msg = f"""
DEPRECATED ADDRESS DETECTED

Address: {address}
Context: {context}
File: {legacy_info['file']}
Contract: {legacy_info['contract']}
Deprecated At: {legacy_info.get('deprecated_at', 'Unknown')}

{legacy_info.get('warning', 'This address is deprecated and should not be used.')}

REMEDIATION:
{self._get_remediation_message(legacy_info)}
"""
            logger.error(error_msg)
            raise ValueError(error_msg.strip())
        
        # Log current address usage for verification
        if normalized_address in self.current_addresses:
            current_info = self.current_addresses[normalized_address]
            logger.debug(f"Using current address {address} from {current_info['file']}")
    
    def _get_remediation_message(self, legacy_info: Dict[str, Any]) -> str:
        """Get remediation message for deprecated address."""
        replacement = legacy_info.get("replacement")
        if replacement:
            return f"Update all references to use the new address: {replacement}"
        else:
            return "Check the current configuration files for the correct address."
    
    def get_current_address(self, contract_name: str, network: str = "base") -> str:
        """
        Get current address for a contract.
        
        Args:
            contract_name: Name of the contract (e.g., "trading")
            network: Network name (e.g., "base")
        
        Returns:
            Current contract address
        
        Raises:
            ValueError: If current address not found
        """
        config_file = self.config_dir / f"{network}.mainnet.json"
        
        if not config_file.exists():
            raise ValueError(f"Configuration file not found: {config_file}")
        
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            contracts = config.get("contracts", {})
            if contract_name not in contracts:
                raise ValueError(f"Contract '{contract_name}' not found in {config_file}")
            
            address = contracts[contract_name].get("address")
            if not address:
                raise ValueError(f"No address specified for contract '{contract_name}'")
            
            return address
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file {config_file}: {e}")
    
    def list_legacy_addresses(self) -> List[Dict[str, Any]]:
        """
        List all legacy addresses with their information.
        
        Returns:
            List of legacy address information
        """
        legacy_list = []
        
        for address, info in self.legacy_addresses.items():
            legacy_list.append({
                "address": address,
                "file": info["file"],
                "contract": info["contract"],
                "deprecated_at": info.get("deprecated_at"),
                "warning": info.get("warning")
            })
        
        return legacy_list
    
    def startup_check(self) -> None:
        """
        Perform startup check for any deprecated addresses in configuration.
        
        This should be called during application startup to ensure
        no deprecated addresses are being used.
        """
        logger.info("Performing startup address validation...")
        
        issues_found = []
        
        # Check all current configuration files for deprecated addresses
        for config_file in self.config_dir.glob("*.mainnet.json"):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                
                contracts = config.get("contracts", {})
                for contract_name, contract_info in contracts.items():
                    address = contract_info.get("address")
                    if address:
                        try:
                            self.validate_address(
                                address,
                                f"{config_file.name}:{contract_name}"
                            )
                        except ValueError as e:
                            issues_found.append(str(e))
                
            except Exception as e:
                logger.error(f"Failed to check config file {config_file}: {e}")
                issues_found.append(f"Config file error: {e}")
        
        if issues_found:
            error_summary = "\n\n".join(issues_found)
            raise ValueError(f"Startup validation failed:\n\n{error_summary}")
        
        logger.info("✅ Startup address validation passed")


# Global instance for easy access
_address_guard = None


def get_address_guard() -> AddressGuard:
    """Get the global address guard instance."""
    global _address_guard
    if _address_guard is None:
        _address_guard = AddressGuard()
    return _address_guard


def validate_contract_address(address: str, context: str = "") -> None:
    """
    Validate a contract address against legacy addresses.
    
    Args:
        address: Contract address to validate
        context: Context information for error messages
    
    Raises:
        ValueError: If address is deprecated
    """
    guard = get_address_guard()
    guard.validate_address(address, context)


def startup_address_check() -> None:
    """
    Perform startup address validation.
    
    Raises:
        ValueError: If deprecated addresses are found
    """
    guard = get_address_guard()
    guard.startup_check()
