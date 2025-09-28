"""
Custom Exception Classes
Centralized error handling for the Vanta Bot
"""

from typing import Optional, Dict, Any


class AppError(Exception):
    """Base application error"""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/serialization"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details
        }


class ConfigError(AppError):
    """Configuration-related errors"""
    pass


class ValidationError(AppError):
    """Input validation errors"""
    pass


class ExternalAPIError(AppError):
    """External API communication errors"""
    
    def __init__(
        self,
        message: str,
        service: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, error_code, details)
        self.service = service
        self.status_code = status_code
        self.response_data = response_data or {}
        self.details.update({
            "service": service,
            "status_code": status_code,
            "response_data": self.response_data
        })


class DatabaseError(AppError):
    """Database operation errors"""
    pass


class BlockchainError(AppError):
    """Blockchain/Web3 related errors"""
    
    def __init__(
        self, 
        message: str, 
        network: str,
        tx_hash: Optional[str] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(message, error_code)
        self.network = network
        self.tx_hash = tx_hash
        self.details.update({
            "network": network,
            "tx_hash": tx_hash
        })


class TradingError(AppError):
    """Trading operation errors"""
    
    def __init__(
        self, 
        message: str, 
        pair: str,
        side: Optional[str] = None,
        amount: Optional[float] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(message, error_code)
        self.pair = pair
        self.side = side
        self.amount = amount
        self.details.update({
            "pair": pair,
            "side": side,
            "amount": amount
        })


class CopyTradingError(AppError):
    """Copy trading specific errors"""
    
    def __init__(
        self, 
        message: str, 
        leader_address: str,
        follower_id: Optional[int] = None,
        pair: Optional[str] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(message, error_code)
        self.leader_address = leader_address
        self.follower_id = follower_id
        self.pair = pair
        self.details.update({
            "leader_address": leader_address,
            "follower_id": follower_id,
            "pair": pair
        })


class TelegramError(AppError):
    """Telegram bot related errors"""
    
    def __init__(
        self, 
        message: str, 
        user_id: Optional[int] = None,
        command: Optional[str] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(message, error_code)
        self.user_id = user_id
        self.command = command
        self.details.update({
            "user_id": user_id,
            "command": command
        })


class RateLimitError(AppError):
    """Rate limiting errors"""
    
    def __init__(
        self, 
        message: str, 
        limit: int,
        window: str,
        user_id: Optional[int] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(message, error_code)
        self.limit = limit
        self.window = window
        self.user_id = user_id
        self.details.update({
            "limit": limit,
            "window": window,
            "user_id": user_id
        })


class SecurityError(AppError):
    """Security-related errors"""
    pass


class InsufficientFundsError(TradingError):
    """Insufficient funds for trading"""

    def __init__(
        self,
        message: str,
        *,
        pair: str,
        required: Optional[float] = None,
        available: Optional[float] = None,
        side: Optional[str] = None,
        amount: Optional[float] = None,
        error_code: Optional[str] = None,
    ):
        super().__init__(message, pair=pair, side=side, amount=amount, error_code=error_code)
        self.required = required
        self.available = available
        if required is not None:
            self.details.update({"required": required})
        if available is not None:
            self.details.update({"available": available})


class InvalidPositionError(TradingError):
    """Invalid position parameters"""

    def __init__(
        self,
        message: str,
        *,
        pair: str,
        size: float,
        side: Optional[str] = None,
        amount: Optional[float] = None,
        error_code: Optional[str] = None,
    ):
        super().__init__(message, pair=pair, side=side, amount=amount, error_code=error_code)
        self.size = size
        self.details.update({"size": size})


class MarketClosedError(TradingError):
    """Market is closed for trading"""
    pass


class SlippageExceededError(TradingError):
    """Slippage tolerance exceeded"""

    def __init__(
        self,
        message: str,
        *,
        pair: str,
        slippage: Optional[float] = None,
        max_slippage: Optional[float] = None,
        side: Optional[str] = None,
        amount: Optional[float] = None,
        error_code: Optional[str] = None,
    ):
        super().__init__(message, pair=pair, side=side, amount=amount, error_code=error_code)
        self.slippage = slippage
        self.max_slippage = max_slippage
        if slippage is not None:
            self.details.update({"slippage": slippage})
        if max_slippage is not None:
            self.details.update({"max_slippage": max_slippage})


class LeaderNotFoundError(CopyTradingError):
    """Copy trading leader not found"""
    pass


class LeaderInactiveError(CopyTradingError):
    """Copy trading leader is inactive"""

    def __init__(
        self,
        message: str,
        *,
        leader_address: str,
        last_activity: int,
        follower_id: Optional[int] = None,
        pair: Optional[str] = None,
        error_code: Optional[str] = None,
    ):
        super().__init__(
            message,
            leader_address=leader_address,
            follower_id=follower_id,
            pair=pair,
            error_code=error_code,
        )
        self.last_activity = last_activity
        self.details.update({"last_activity": last_activity})


class CopyLimitExceededError(CopyTradingError):
    """Copy trading limits exceeded"""

    def __init__(
        self,
        message: str,
        *,
        leader_address: str,
        current_count: int,
        max_count: int,
        follower_id: Optional[int] = None,
        pair: Optional[str] = None,
        error_code: Optional[str] = None,
    ):
        super().__init__(
            message,
            leader_address=leader_address,
            follower_id=follower_id,
            pair=pair,
            error_code=error_code,
        )
        self.current_count = current_count
        self.max_count = max_count
        self.details.update({"current_count": current_count, "max_count": max_count})


def handle_exception(exc: Exception, context: Optional[Dict[str, Any]] = None) -> AppError:
    """Convert any exception to AppError with context"""
    if isinstance(exc, AppError):
        if context:
            exc.details.update(context)
        return exc
    
    # Convert common exceptions to AppError
    if isinstance(exc, ValueError):
        return ValidationError(str(exc), details=context or {})
    elif isinstance(exc, KeyError):
        key = exc.args[0] if exc.args else "unknown"
        return ConfigError(f"Missing configuration: {key}", details=context or {})
    elif isinstance(exc, ConnectionError):
        return ExternalAPIError(
            f"Connection failed: {exc}",
            service="unknown",
            details=context or {},
        )
    elif isinstance(exc, TimeoutError):
        return ExternalAPIError(
            f"Request timeout: {exc}",
            service="unknown",
            details=context or {},
        )
    else:
        return AppError(
            f"Unexpected error: {exc}", 
            error_code="UNEXPECTED_ERROR",
            details=context or {}
        )


def format_error_for_user(error: AppError) -> str:
    """Format error message for user display"""
    if isinstance(error, ValidationError):
        return f"❌ Invalid input: {error.message}"
    elif isinstance(error, InsufficientFundsError):
        return f"💰 Insufficient funds: {error.message}"
    elif isinstance(error, RateLimitError):
        return f"⏱️ Rate limit exceeded: {error.message}"
    elif isinstance(error, MarketClosedError):
        return f"🔒 Market closed: {error.message}"
    elif isinstance(error, SlippageExceededError):
        return f"📈 Slippage too high: {error.message}"
    elif isinstance(error, CopyTradingError):
        return f"📊 Copy trading error: {error.message}"
    elif isinstance(error, TelegramError):
        return f"🤖 Bot error: {error.message}"
    elif isinstance(error, ExternalAPIError):
        return f"🌐 Service temporarily unavailable: {error.message}"
    elif isinstance(error, BlockchainError):
        return f"⛓️ Blockchain error: {error.message}"
    else:
        return f"❌ Error: {error.message}"
