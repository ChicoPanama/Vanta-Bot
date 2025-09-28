"""Symbol normalization utilities for oracle providers."""

from typing import Dict, Optional, List


# UI format to canonical provider format mapping
UI_TO_CANONICAL: Dict[str, str] = {
    'BTC/USD': 'BTC',
    'ETH/USD': 'ETH', 
    'SOL/USD': 'SOL',
    'CBBTC/USD': 'CBBTC',
    'CBETH/USD': 'CBETH',
    'AERO/USD': 'AERO',
    'EUR/USD': 'EUR',
    'XAU/USD': 'XAU',
    'EURC/USD': 'EURC',
}

# Canonical provider format to UI format mapping
CANONICAL_TO_UI: Dict[str, str] = {
    'BTC': 'BTC/USD',
    'ETH': 'ETH/USD',
    'SOL': 'SOL/USD',
    'CBBTC': 'CBBTC/USD',
    'CBETH': 'CBETH/USD',
    'AERO': 'AERO/USD',
    'EUR': 'EUR/USD',
    'XAU': 'XAU/USD',
    'EURC': 'EURC/USD',
}


def to_canonical(symbol: str) -> str:
    """
    Convert UI symbol format (e.g., 'BTC/USD') to canonical provider format (e.g., 'BTC').
    If symbol has no '/', return it unchanged (already canonical).
    
    Args:
        symbol: Symbol in UI format (e.g., 'BTC/USD', 'ETH/USD') or canonical (e.g., 'BTC')
        
    Returns:
        Canonical symbol for provider lookups (e.g., 'BTC', 'ETH')
        
    Example:
        >>> to_canonical('BTC/USD')
        'BTC'
        >>> to_canonical('BTC')
        'BTC'
        >>> to_canonical('ETH/USD')
        'ETH'
    """
    upper_symbol = symbol.upper()
    if '/' not in upper_symbol:
        return upper_symbol  # Already canonical
    return UI_TO_CANONICAL.get(upper_symbol, upper_symbol)


def to_ui_format(symbol: str) -> str:
    """
    Convert canonical provider format (e.g., 'BTC') to UI format (e.g., 'BTC/USD').
    
    Args:
        symbol: Canonical symbol from provider (e.g., 'BTC', 'ETH')
        
    Returns:
        UI-formatted symbol (e.g., 'BTC/USD', 'ETH/USD')
        
    Example:
        >>> to_ui_format('BTC')
        'BTC/USD'
        >>> to_ui_format('ETH')
        'ETH/USD'
    """
    return CANONICAL_TO_UI.get(symbol.upper(), f"{symbol.upper()}/USD")


def get_available_symbols() -> List[str]:
    """
    Get list of all available symbols in UI format.
    
    Returns:
        List of symbols in UI format (e.g., ['BTC/USD', 'ETH/USD', ...])
    """
    return list(UI_TO_CANONICAL.keys())


def is_supported_symbol(symbol: str) -> bool:
    """
    Check if a symbol is supported by the oracle providers.
    
    Args:
        symbol: Symbol to check (can be in UI or canonical format)
        
    Returns:
        True if symbol is supported, False otherwise
    """
    canonical = to_canonical(symbol)
    return canonical in CANONICAL_TO_UI.keys()
