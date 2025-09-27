import re

def validate_trade_size(size: float) -> bool:
    return 1.0 <= size <= 100000.0

def validate_leverage(leverage: int) -> bool:
    return leverage in [2, 5, 10, 25, 50, 100, 250, 500]

def validate_symbol(symbol: str) -> bool:
    valid_symbols = ['BTC', 'ETH', 'SOL', 'EURUSD', 'GBPUSD', 'USDJPY']
    return symbol in valid_symbols
