"""Base signer interface for transaction signing."""

from typing import Protocol, Dict, Any
from abc import ABC, abstractmethod


class Signer(Protocol):
    """Signer interface for transaction signing."""
    
    @property
    def address(self) -> str:
        """Get the signer's address."""
        ...
    
    async def sign_and_send(self, tx: Dict[str, Any]) -> str:
        """Sign and send transaction.
        
        Args:
            tx: Transaction dictionary with 'to', 'data', 'value', 'gas', 'nonce', etc.
            
        Returns:
            Transaction hash
        """
        ...
