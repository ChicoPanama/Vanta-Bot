"""Unit tests for symbol normalization utilities."""

import pytest
from src.services.markets.symbols import (
    to_canonical, 
    to_ui_format, 
    get_available_symbols, 
    is_supported_symbol
)


class TestSymbolNormalization:
    """Test symbol normalization functions."""
    
    def test_to_canonical_ui_format(self):
        """Test converting UI format to canonical."""
        assert to_canonical('BTC/USD') == 'BTC'
        assert to_canonical('ETH/USD') == 'ETH'
        assert to_canonical('SOL/USD') == 'SOL'
        assert to_canonical('CBBTC/USD') == 'CBBTC'
        assert to_canonical('CBETH/USD') == 'CBETH'
        assert to_canonical('AERO/USD') == 'AERO'
        assert to_canonical('EUR/USD') == 'EUR'
        assert to_canonical('XAU/USD') == 'XAU'
        assert to_canonical('EURC/USD') == 'EURC'
    
    def test_to_canonical_already_canonical(self):
        """Test that canonical symbols remain unchanged."""
        assert to_canonical('BTC') == 'BTC'
        assert to_canonical('ETH') == 'ETH'
        assert to_canonical('SOL') == 'SOL'
        assert to_canonical('CBBTC') == 'CBBTC'
        assert to_canonical('CBETH') == 'CBETH'
        assert to_canonical('AERO') == 'AERO'
        assert to_canonical('EUR') == 'EUR'
        assert to_canonical('XAU') == 'XAU'
        assert to_canonical('EURC') == 'EURC'
    
    def test_to_canonical_case_insensitive(self):
        """Test case insensitive conversion."""
        assert to_canonical('btc/usd') == 'BTC'
        assert to_canonical('Btc/Usd') == 'BTC'
        assert to_canonical('ETH') == 'ETH'
        assert to_canonical('eth') == 'ETH'
    
    def test_to_canonical_unknown_symbol(self):
        """Test unknown symbols return unchanged."""
        assert to_canonical('UNKNOWN/USD') == 'UNKNOWN/USD'
        assert to_canonical('UNKNOWN') == 'UNKNOWN'
    
    def test_to_ui_format_canonical(self):
        """Test converting canonical to UI format."""
        assert to_ui_format('BTC') == 'BTC/USD'
        assert to_ui_format('ETH') == 'ETH/USD'
        assert to_ui_format('SOL') == 'SOL/USD'
        assert to_ui_format('CBBTC') == 'CBBTC/USD'
        assert to_ui_format('CBETH') == 'CBETH/USD'
        assert to_ui_format('AERO') == 'AERO/USD'
        assert to_ui_format('EUR') == 'EUR/USD'
        assert to_ui_format('XAU') == 'XAU/USD'
        assert to_ui_format('EURC') == 'EURC/USD'
    
    def test_to_ui_format_case_insensitive(self):
        """Test case insensitive UI format conversion."""
        assert to_ui_format('btc') == 'BTC/USD'
        assert to_ui_format('Btc') == 'BTC/USD'
        assert to_ui_format('ETH') == 'ETH/USD'
        assert to_ui_format('eth') == 'ETH/USD'
    
    def test_to_ui_format_unknown_symbol(self):
        """Test unknown symbols get default USD suffix."""
        assert to_ui_format('UNKNOWN') == 'UNKNOWN/USD'
        assert to_ui_format('NEWCOIN') == 'NEWCOIN/USD'
    
    def test_get_available_symbols(self):
        """Test getting available symbols in UI format."""
        symbols = get_available_symbols()
        assert 'BTC/USD' in symbols
        assert 'ETH/USD' in symbols
        assert 'SOL/USD' in symbols
        assert 'CBBTC/USD' in symbols
        assert 'CBETH/USD' in symbols
        assert 'AERO/USD' in symbols
        assert 'EUR/USD' in symbols
        assert 'XAU/USD' in symbols
        assert 'EURC/USD' in symbols
        assert len(symbols) == 9
    
    def test_is_supported_symbol_ui_format(self):
        """Test checking supported symbols in UI format."""
        assert is_supported_symbol('BTC/USD') == True
        assert is_supported_symbol('ETH/USD') == True
        assert is_supported_symbol('SOL/USD') == True
        assert is_supported_symbol('CBBTC/USD') == True
        assert is_supported_symbol('CBETH/USD') == True
        assert is_supported_symbol('AERO/USD') == True
        assert is_supported_symbol('EUR/USD') == True
        assert is_supported_symbol('XAU/USD') == True
        assert is_supported_symbol('EURC/USD') == True
    
    def test_is_supported_symbol_canonical(self):
        """Test checking supported symbols in canonical format."""
        assert is_supported_symbol('BTC') == True
        assert is_supported_symbol('ETH') == True
        assert is_supported_symbol('SOL') == True
        assert is_supported_symbol('CBBTC') == True
        assert is_supported_symbol('CBETH') == True
        assert is_supported_symbol('AERO') == True
        assert is_supported_symbol('EUR') == True
        assert is_supported_symbol('XAU') == True
        assert is_supported_symbol('EURC') == True
    
    def test_is_supported_symbol_case_insensitive(self):
        """Test case insensitive symbol checking."""
        assert is_supported_symbol('btc') == True
        assert is_supported_symbol('Btc') == True
        assert is_supported_symbol('btc/usd') == True
        assert is_supported_symbol('Btc/Usd') == True
    
    def test_is_supported_symbol_unsupported(self):
        """Test unsupported symbols return False."""
        assert is_supported_symbol('UNKNOWN') == False
        assert is_supported_symbol('UNKNOWN/USD') == False
        assert is_supported_symbol('NEWCOIN') == False
        assert is_supported_symbol('NEWCOIN/USD') == False
    
    def test_round_trip_conversion(self):
        """Test round-trip conversion maintains consistency."""
        ui_symbols = get_available_symbols()
        for ui_symbol in ui_symbols:
            canonical = to_canonical(ui_symbol)
            back_to_ui = to_ui_format(canonical)
            assert back_to_ui == ui_symbol, f"Round trip failed: {ui_symbol} -> {canonical} -> {back_to_ui}"
    
    def test_no_symbol_flipping(self):
        """Test that canonical symbols don't flip to UI format."""
        canonical_symbols = ['BTC', 'ETH', 'SOL', 'CBBTC', 'CBETH', 'AERO', 'EUR', 'XAU', 'EURC']
        for symbol in canonical_symbols:
            result = to_canonical(symbol)
            assert result == symbol, f"Symbol {symbol} was flipped to {result}"
            assert '/' not in result, f"Canonical symbol {symbol} contains '/' in result {result}"
