"""
Input Validation Utilities
Common validation functions for user input
"""

import re
from typing import Any, Dict, List, Optional, Union
from decimal import Decimal, InvalidOperation

from src.bot.constants import MAX_LEVERAGE, MIN_POSITION_SIZE, MAX_POSITION_SIZE
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ValidationError(Exception):
    """Custom validation error"""
    pass


def validate_user_input(func):
    """Decorator to validate user input for handlers"""
    def wrapper(*args, **kwargs):
        # Extract update and context from args
        update = args[0] if args else None
        context = args[1] if len(args) > 1 else None
        
        if update and context:
            # Validate user input based on handler type
            try:
                if update.message and update.message.text:
                    validate_text_input(update.message.text)
                elif update.callback_query:
                    validate_callback_data(update.callback_query.data)
            except ValidationError as e:
                logger.warning(f"Input validation failed: {e}")
                # Could send error message to user here
                return None
        
        return func(*args, **kwargs)
    return wrapper


def validate_text_input(text: str) -> bool:
    """Validate text input from users"""
    if not text or not isinstance(text, str):
        raise ValidationError("Invalid text input")
    
    # Check for potentially harmful content
    if len(text) > 1000:
        raise ValidationError("Input too long")
    
    # Check for SQL injection patterns
    sql_patterns = [
        r'(union|select|insert|update|delete|drop|create|alter)\s+',
        r'(or|and)\s+1\s*=\s*1',
        r';\s*(drop|delete|update|insert)',
    ]
    
    for pattern in sql_patterns:
        if re.search(pattern, text.lower()):
            raise ValidationError("Invalid input pattern detected")
    
    return True


def validate_callback_data(callback_data: str) -> bool:
    """Validate callback query data"""
    if not callback_data or not isinstance(callback_data, str):
        raise ValidationError("Invalid callback data")
    
    if len(callback_data) > 100:
        raise ValidationError("Callback data too long")
    
    # Check for valid callback patterns
    valid_patterns = [
        r'^[a-z_]+$',  # Simple commands
        r'^[a-z_]+_[a-z0-9_]+$',  # Commands with parameters
        r'^settings_[a-z]+$',  # Settings commands
        r'^trade_[a-z]+$',  # Trading commands
        r'^quick_[a-z0-9]+$',  # Quick trade commands
    ]
    
    if not any(re.match(pattern, callback_data) for pattern in valid_patterns):
        raise ValidationError("Invalid callback data pattern")
    
    return True


def validate_trade_size(size: Union[str, float, int]) -> float:
    """Validate trade size input"""
    try:
        if isinstance(size, str):
            # Parse string input
            size = float(size.replace('$', '').replace(',', ''))
        
        size = float(size)
        
        if size < MIN_POSITION_SIZE:
            raise ValidationError(f"Trade size too small. Minimum: ${MIN_POSITION_SIZE}")
        
        if size > MAX_POSITION_SIZE:
            raise ValidationError(f"Trade size too large. Maximum: ${MAX_POSITION_SIZE}")
        
        return size
    
    except (ValueError, InvalidOperation):
        raise ValidationError("Invalid trade size format")


def validate_leverage(leverage: Union[str, int]) -> int:
    """Validate leverage input"""
    try:
        if isinstance(leverage, str):
            leverage = int(leverage.replace('x', ''))
        
        leverage = int(leverage)
        
        if leverage < 1:
            raise ValidationError("Leverage must be at least 1x")
        
        if leverage > MAX_LEVERAGE:
            raise ValidationError(f"Leverage too high. Maximum: {MAX_LEVERAGE}x")
        
        return leverage
    
    except (ValueError, TypeError):
        raise ValidationError("Invalid leverage format")


def validate_asset_symbol(symbol: str) -> bool:
    """Validate asset symbol"""
    if not symbol or not isinstance(symbol, str):
        raise ValidationError("Invalid asset symbol")
    
    # Check for valid asset patterns
    valid_patterns = [
        r'^[A-Z]{2,6}$',  # Crypto symbols like BTC, ETH
        r'^[A-Z]{3}/[A-Z]{3}$',  # Forex pairs like EUR/USD
        r'^[A-Z]+-[A-Z]+$',  # Trading pairs like BTC-USD
    ]
    
    if not any(re.match(pattern, symbol) for pattern in valid_patterns):
        raise ValidationError("Invalid asset symbol format")
    
    return True


def validate_wallet_address(address: str) -> bool:
    """Validate wallet address format"""
    if not address or not isinstance(address, str):
        raise ValidationError("Invalid wallet address")
    
    # Ethereum address pattern (Base network uses same format)
    eth_pattern = r'^0x[a-fA-F0-9]{40}$'
    
    if not re.match(eth_pattern, address):
        raise ValidationError("Invalid wallet address format")
    
    return True


def validate_user_id(user_id: Union[str, int]) -> int:
    """Validate user ID"""
    try:
        user_id = int(user_id)
        
        if user_id <= 0:
            raise ValidationError("Invalid user ID")
        
        return user_id
    
    except (ValueError, TypeError):
        raise ValidationError("Invalid user ID format")


def validate_position_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate position creation/update data"""
    required_fields = ['symbol', 'side', 'size', 'leverage']
    
    for field in required_fields:
        if field not in data:
            raise ValidationError(f"Missing required field: {field}")
    
    # Validate individual fields
    validate_asset_symbol(data['symbol'])
    
    if data['side'] not in ['LONG', 'SHORT']:
        raise ValidationError("Invalid position side. Must be LONG or SHORT")
    
    data['size'] = validate_trade_size(data['size'])
    data['leverage'] = validate_leverage(data['leverage'])
    
    return data


def sanitize_user_input(text: str) -> str:
    """Sanitize user input for safe processing"""
    if not text:
        return ""
    
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>"\']', '', text)
    
    # Limit length
    if len(sanitized) > 500:
        sanitized = sanitized[:500]
    
    return sanitized.strip()