"""
Test error handling and custom exceptions
"""
import pytest

from src.utils.errors import (
    AppError, ConfigError, ValidationError, ExternalAPIError,
    DatabaseError, BlockchainError, TradingError, CopyTradingError,
    TelegramError, RateLimitError, SecurityError,
    InsufficientFundsError, InvalidPositionError, MarketClosedError,
    SlippageExceededError, LeaderNotFoundError, LeaderInactiveError,
    CopyLimitExceededError, handle_exception, format_error_for_user
)


class TestAppError:
    """Test base AppError class"""
    
    def test_app_error_basic(self):
        """Test basic AppError creation"""
        error = AppError("Test error message")
        
        assert error.message == "Test error message"
        assert error.error_code is None
        assert error.details == {}
        assert str(error) == "Test error message"
    
    def test_app_error_with_code(self):
        """Test AppError with error code"""
        error = AppError("Test error", error_code="TEST_ERROR")
        
        assert error.message == "Test error"
        assert error.error_code == "TEST_ERROR"
        assert error.details == {}
    
    def test_app_error_with_details(self):
        """Test AppError with details"""
        details = {"field": "value", "count": 42}
        error = AppError("Test error", details=details)
        
        assert error.message == "Test error"
        assert error.details == details
    
    def test_app_error_to_dict(self):
        """Test AppError to_dict method"""
        error = AppError(
            "Test error",
            error_code="TEST_ERROR",
            details={"field": "value"}
        )
        
        result = error.to_dict()
        
        assert result["error_type"] == "AppError"
        assert result["message"] == "Test error"
        assert result["error_code"] == "TEST_ERROR"
        assert result["details"] == {"field": "value"}


class TestSpecificErrors:
    """Test specific error types"""
    
    def test_config_error(self):
        """Test ConfigError"""
        error = ConfigError("Configuration error")
        
        assert isinstance(error, AppError)
        assert error.message == "Configuration error"
    
    def test_validation_error(self):
        """Test ValidationError"""
        error = ValidationError("Validation failed")
        
        assert isinstance(error, AppError)
        assert error.message == "Validation failed"
    
    def test_external_api_error(self):
        """Test ExternalAPIError"""
        error = ExternalAPIError(
            "API call failed",
            service="telegram",
            status_code=500,
            response_data={"error": "Internal server error"}
        )
        
        assert isinstance(error, AppError)
        assert error.message == "API call failed"
        assert error.service == "telegram"
        assert error.status_code == 500
        assert error.response_data == {"error": "Internal server error"}
        assert "service" in error.details
        assert "status_code" in error.details
        assert "response_data" in error.details
    
    def test_database_error(self):
        """Test DatabaseError"""
        error = DatabaseError("Database connection failed")
        
        assert isinstance(error, AppError)
        assert error.message == "Database connection failed"
    
    def test_blockchain_error(self):
        """Test BlockchainError"""
        error = BlockchainError(
            "Transaction failed",
            network="base",
            tx_hash="0x123"
        )
        
        assert isinstance(error, AppError)
        assert error.message == "Transaction failed"
        assert error.network == "base"
        assert error.tx_hash == "0x123"
        assert "network" in error.details
        assert "tx_hash" in error.details
    
    def test_trading_error(self):
        """Test TradingError"""
        error = TradingError(
            "Trade failed",
            pair="ETH/USD",
            side="long",
            amount=100.0
        )
        
        assert isinstance(error, AppError)
        assert error.message == "Trade failed"
        assert error.pair == "ETH/USD"
        assert error.side == "long"
        assert error.amount == 100.0
        assert "pair" in error.details
        assert "side" in error.details
        assert "amount" in error.details
    
    def test_copy_trading_error(self):
        """Test CopyTradingError"""
        error = CopyTradingError(
            "Copy trade failed",
            leader_address="0x123",
            follower_id=456,
            pair="BTC/USD"
        )
        
        assert isinstance(error, AppError)
        assert error.message == "Copy trade failed"
        assert error.leader_address == "0x123"
        assert error.follower_id == 456
        assert error.pair == "BTC/USD"
        assert "leader_address" in error.details
        assert "follower_id" in error.details
        assert "pair" in error.details
    
    def test_telegram_error(self):
        """Test TelegramError"""
        error = TelegramError(
            "Telegram API error",
            user_id=123,
            command="/start"
        )
        
        assert isinstance(error, AppError)
        assert error.message == "Telegram API error"
        assert error.user_id == 123
        assert error.command == "/start"
        assert "user_id" in error.details
        assert "command" in error.details
    
    def test_rate_limit_error(self):
        """Test RateLimitError"""
        error = RateLimitError(
            "Rate limit exceeded",
            limit=10,
            window="1 minute",
            user_id=123
        )
        
        assert isinstance(error, AppError)
        assert error.message == "Rate limit exceeded"
        assert error.limit == 10
        assert error.window == "1 minute"
        assert error.user_id == 123
        assert "limit" in error.details
        assert "window" in error.details
        assert "user_id" in error.details
    
    def test_security_error(self):
        """Test SecurityError"""
        error = SecurityError("Security violation")
        
        assert isinstance(error, AppError)
        assert error.message == "Security violation"


class TestTradingSpecificErrors:
    """Test trading-specific error types"""
    
    def test_insufficient_funds_error(self):
        """Test InsufficientFundsError"""
        error = InsufficientFundsError(
            "Insufficient funds",
            pair="ETH/USD",
            required=100.0,
            available=50.0
        )
        
        assert isinstance(error, TradingError)
        assert isinstance(error, AppError)
        assert error.message == "Insufficient funds"
        assert error.pair == "ETH/USD"
    
    def test_invalid_position_error(self):
        """Test InvalidPositionError"""
        error = InvalidPositionError(
            "Invalid position size",
            pair="BTC/USD",
            size=-100.0
        )
        
        assert isinstance(error, TradingError)
        assert isinstance(error, AppError)
        assert error.message == "Invalid position size"
        assert error.pair == "BTC/USD"
    
    def test_market_closed_error(self):
        """Test MarketClosedError"""
        error = MarketClosedError(
            "Market is closed",
            pair="EUR/USD"
        )
        
        assert isinstance(error, TradingError)
        assert isinstance(error, AppError)
        assert error.message == "Market is closed"
        assert error.pair == "EUR/USD"
    
    def test_slippage_exceeded_error(self):
        """Test SlippageExceededError"""
        error = SlippageExceededError(
            "Slippage too high",
            pair="ETH/USD",
            slippage=5.0,
            max_slippage=2.0
        )
        
        assert isinstance(error, TradingError)
        assert isinstance(error, AppError)
        assert error.message == "Slippage too high"
        assert error.pair == "ETH/USD"


class TestCopyTradingSpecificErrors:
    """Test copy trading-specific error types"""
    
    def test_leader_not_found_error(self):
        """Test LeaderNotFoundError"""
        error = LeaderNotFoundError(
            "Leader not found",
            leader_address="0x123"
        )
        
        assert isinstance(error, CopyTradingError)
        assert isinstance(error, AppError)
        assert error.message == "Leader not found"
        assert error.leader_address == "0x123"
    
    def test_leader_inactive_error(self):
        """Test LeaderInactiveError"""
        error = LeaderInactiveError(
            "Leader is inactive",
            leader_address="0x123",
            last_activity=1234567890
        )
        
        assert isinstance(error, CopyTradingError)
        assert isinstance(error, AppError)
        assert error.message == "Leader is inactive"
        assert error.leader_address == "0x123"
    
    def test_copy_limit_exceeded_error(self):
        """Test CopyLimitExceededError"""
        error = CopyLimitExceededError(
            "Copy limit exceeded",
            leader_address="0x123",
            current_count=10,
            max_count=5
        )
        
        assert isinstance(error, CopyTradingError)
        assert isinstance(error, AppError)
        assert error.message == "Copy limit exceeded"
        assert error.leader_address == "0x123"


class TestErrorHandling:
    """Test error handling utilities"""
    
    def test_handle_exception_app_error(self):
        """Test handle_exception with AppError"""
        original_error = AppError("Original error", error_code="ORIGINAL")
        context = {"user_id": 123}
        
        result = handle_exception(original_error, context)
        
        assert result is original_error
        assert result.details == context
    
    def test_handle_exception_value_error(self):
        """Test handle_exception with ValueError"""
        original_error = ValueError("Invalid value")
        context = {"field": "test"}
        
        result = handle_exception(original_error, context)
        
        assert isinstance(result, ValidationError)
        assert result.message == "Invalid value"
        assert result.details == context
    
    def test_handle_exception_key_error(self):
        """Test handle_exception with KeyError"""
        original_error = KeyError("missing_key")
        context = {"config_file": "settings.py"}
        
        result = handle_exception(original_error, context)
        
        assert isinstance(result, ConfigError)
        assert "Missing configuration: missing_key" in result.message
        assert result.details == context
    
    def test_handle_exception_connection_error(self):
        """Test handle_exception with ConnectionError"""
        original_error = ConnectionError("Connection failed")
        context = {"service": "database"}
        
        result = handle_exception(original_error, context)
        
        assert isinstance(result, ExternalAPIError)
        assert "Connection failed" in result.message
        assert result.service == "unknown"
        assert result.details == context
    
    def test_handle_exception_timeout_error(self):
        """Test handle_exception with TimeoutError"""
        original_error = TimeoutError("Request timeout")
        context = {"timeout": 30}
        
        result = handle_exception(original_error, context)
        
        assert isinstance(result, ExternalAPIError)
        assert "Request timeout" in result.message
        assert result.service == "unknown"
        assert result.details == context
    
    def test_handle_exception_generic(self):
        """Test handle_exception with generic exception"""
        original_error = RuntimeError("Unexpected error")
        context = {"operation": "test"}
        
        result = handle_exception(original_error, context)
        
        assert isinstance(result, AppError)
        assert "Unexpected error" in result.message
        assert result.error_code == "UNEXPECTED_ERROR"
        assert result.details == context


class TestErrorFormatting:
    """Test error formatting for user display"""
    
    def test_format_validation_error(self):
        """Test formatting ValidationError"""
        error = ValidationError("Invalid input")
        result = format_error_for_user(error)
        
        assert result == "❌ Invalid input: Invalid input"
    
    def test_format_insufficient_funds_error(self):
        """Test formatting InsufficientFundsError"""
        error = InsufficientFundsError("Not enough funds", pair="ETH/USD")
        result = format_error_for_user(error)
        
        assert result == "💰 Insufficient funds: Not enough funds"
    
    def test_format_rate_limit_error(self):
        """Test formatting RateLimitError"""
        error = RateLimitError("Too many requests", limit=10, window="1 minute")
        result = format_error_for_user(error)
        
        assert result == "⏱️ Rate limit exceeded: Too many requests"
    
    def test_format_market_closed_error(self):
        """Test formatting MarketClosedError"""
        error = MarketClosedError("Market closed", pair="EUR/USD")
        result = format_error_for_user(error)
        
        assert result == "🔒 Market closed: Market closed"
    
    def test_format_slippage_exceeded_error(self):
        """Test formatting SlippageExceededError"""
        error = SlippageExceededError("Slippage too high", pair="ETH/USD")
        result = format_error_for_user(error)
        
        assert result == "📈 Slippage too high: Slippage too high"
    
    def test_format_copy_trading_error(self):
        """Test formatting CopyTradingError"""
        error = CopyTradingError("Copy failed", leader_address="0x123")
        result = format_error_for_user(error)
        
        assert result == "📊 Copy trading error: Copy failed"
    
    def test_format_telegram_error(self):
        """Test formatting TelegramError"""
        error = TelegramError("Bot error", user_id=123)
        result = format_error_for_user(error)
        
        assert result == "🤖 Bot error: Bot error"
    
    def test_format_external_api_error(self):
        """Test formatting ExternalAPIError"""
        error = ExternalAPIError("API down", service="telegram")
        result = format_error_for_user(error)
        
        assert result == "🌐 Service temporarily unavailable: API down"
    
    def test_format_blockchain_error(self):
        """Test formatting BlockchainError"""
        error = BlockchainError("Transaction failed", network="base")
        result = format_error_for_user(error)
        
        assert result == "⛓️ Blockchain error: Transaction failed"
    
    def test_format_generic_error(self):
        """Test formatting generic AppError"""
        error = AppError("Generic error")
        result = format_error_for_user(error)
        
        assert result == "❌ Error: Generic error"
