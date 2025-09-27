"""
Telemetry Middleware
Structured telemetry and monitoring for Telegram bot handlers
"""

import time
import asyncio
from typing import Callable, Any, Dict, Optional
from functools import wraps
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import ContextTypes

from src.utils.logging import get_logger, log_telegram_command, log_trade_execution, log_copy_trade, log_performance
from src.utils.errors import AppError, format_error_for_user
from src.config.flags import flags

logger = get_logger(__name__)


class TelemetryMiddleware:
    """Middleware for collecting telemetry data from bot handlers"""
    
    def __init__(self):
        self.command_stats = {}
        self.error_stats = {}
        self.performance_stats = {}
    
    def track_command(
        self,
        command_name: Optional[str] = None,
        track_user: bool = True,
        track_performance: bool = True
    ):
        """Decorator to track Telegram command execution"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
                start_time = time.time()
                user_id = update.effective_user.id if update.effective_user else None
                command = command_name or (update.message.text.split()[0] if update.message and update.message.text else "unknown")
                
                # Initialize stats for this command
                if command not in self.command_stats:
                    self.command_stats[command] = {
                        "count": 0,
                        "success_count": 0,
                        "error_count": 0,
                        "total_time": 0.0,
                        "avg_time": 0.0,
                        "last_execution": None
                    }
                
                success = False
                error = None
                
                try:
                    # Log command start
                    if track_user and user_id:
                        logger.info(f"Command started: {command}", extra={
                            "user_id_hash": hash(str(user_id)),
                            "command": command,
                            "chat_id": update.effective_chat.id if update.effective_chat else None
                        })
                    
                    # Execute the command
                    result = await func(update, context)
                    success = True
                    
                    return result
                    
                except AppError as e:
                    error = e
                    success = False
                    
                    # Log structured error
                    logger.error(f"Command failed with AppError: {command}", extra={
                        "user_id_hash": hash(str(user_id)) if track_user and user_id else None,
                        "command": command,
                        "error_type": e.__class__.__name__,
                        "error_code": e.error_code,
                        "error_message": e.message
                    })
                    
                    # Send user-friendly error message
                    if update.effective_chat:
                        await update.effective_chat.send_message(
                            format_error_for_user(e)
                        )
                    
                    raise
                    
                except Exception as e:
                    error = e
                    success = False
                    
                    # Log unexpected error
                    logger.error(f"Command failed with unexpected error: {command}", extra={
                        "user_id_hash": hash(str(user_id)) if track_user and user_id else None,
                        "command": command,
                        "error_type": e.__class__.__name__,
                        "error_message": str(e)
                    })
                    
                    # Send generic error message
                    if update.effective_chat:
                        await update.effective_chat.send_message(
                            "❌ An unexpected error occurred. Please try again later."
                        )
                    
                    raise
                    
                finally:
                    # Calculate execution time
                    execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                    
                    # Update stats
                    stats = self.command_stats[command]
                    stats["count"] += 1
                    stats["last_execution"] = datetime.now(timezone.utc).isoformat()
                    
                    if success:
                        stats["success_count"] += 1
                    else:
                        stats["error_count"] += 1
                    
                    if track_performance:
                        stats["total_time"] += execution_time
                        stats["avg_time"] = stats["total_time"] / stats["count"]
                    
                    # Log command completion
                    if track_user and user_id:
                        log_telegram_command(
                            user_id=user_id,
                            command=command,
                            success=success,
                            duration_ms=execution_time
                        )
                    
                    # Log performance if enabled
                    if track_performance:
                        log_performance(
                            operation=f"telegram_command_{command}",
                            duration_ms=execution_time,
                            success=success,
                            user_id_hash=hash(str(user_id)) if track_user and user_id else None
                        )
            
            return wrapper
        return decorator
    
    def track_trade_execution(
        self,
        track_user: bool = True,
        track_performance: bool = True
    ):
        """Decorator to track trade execution"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs) -> Any:
                start_time = time.time()
                
                # Extract trade parameters from function arguments
                user_id = kwargs.get('user_id') or (args[0] if args else None)
                pair = kwargs.get('pair', 'unknown')
                side = kwargs.get('side', 'unknown')
                amount = kwargs.get('amount', 0.0)
                mode = kwargs.get('mode', flags.execution_mode().value)
                
                success = False
                tx_hash = None
                
                try:
                    # Execute the trade
                    result = await func(*args, **kwargs)
                    success = True
                    
                    # Extract transaction hash if available
                    if isinstance(result, dict) and 'tx_hash' in result:
                        tx_hash = result['tx_hash']
                    elif isinstance(result, str) and result != "DRYRUN":
                        tx_hash = result
                    
                    return result
                    
                except Exception as e:
                    success = False
                    logger.error(f"Trade execution failed: {pair} {side}", extra={
                        "user_id_hash": hash(str(user_id)) if track_user and user_id else None,
                        "pair": pair,
                        "side": side,
                        "amount": amount,
                        "mode": mode,
                        "error": str(e)
                    })
                    raise
                    
                finally:
                    # Calculate execution time
                    execution_time = (time.time() - start_time) * 1000
                    
                    # Log trade execution
                    if track_user and user_id:
                        log_trade_execution(
                            user_id=user_id,
                            pair=pair,
                            side=side,
                            amount=amount,
                            mode=mode,
                            success=success,
                            tx_hash=tx_hash
                        )
                    
                    # Log performance if enabled
                    if track_performance:
                        log_performance(
                            operation="trade_execution",
                            duration_ms=execution_time,
                            success=success,
                            pair=pair,
                            side=side,
                            mode=mode
                        )
            
            return wrapper
        return decorator
    
    def track_copy_trade(
        self,
        track_user: bool = True,
        track_performance: bool = True
    ):
        """Decorator to track copy trade execution"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs) -> Any:
                start_time = time.time()
                
                # Extract copy trade parameters
                follower_id = kwargs.get('follower_id') or (args[0] if args else None)
                leader_address = kwargs.get('leader_address', 'unknown')
                pair = kwargs.get('pair', 'unknown')
                amount = kwargs.get('amount', 0.0)
                
                success = False
                reason = None
                
                try:
                    # Execute the copy trade
                    result = await func(*args, **kwargs)
                    success = True
                    
                    return result
                    
                except Exception as e:
                    success = False
                    reason = str(e)
                    logger.error(f"Copy trade execution failed: {leader_address} -> {follower_id}", extra={
                        "follower_id_hash": hash(str(follower_id)) if track_user and follower_id else None,
                        "leader_address": leader_address,
                        "pair": pair,
                        "amount": amount,
                        "error": str(e)
                    })
                    raise
                    
                finally:
                    # Calculate execution time
                    execution_time = (time.time() - start_time) * 1000
                    
                    # Log copy trade execution
                    if track_user and follower_id:
                        log_copy_trade(
                            follower_id=follower_id,
                            leader_address=leader_address,
                            pair=pair,
                            amount=amount,
                            success=success,
                            reason=reason
                        )
                    
                    # Log performance if enabled
                    if track_performance:
                        log_performance(
                            operation="copy_trade_execution",
                            duration_ms=execution_time,
                            success=success,
                            leader_address=leader_address,
                            pair=pair
                        )
            
            return wrapper
        return decorator
    
    def track_performance(
        self,
        operation_name: str,
        track_user: bool = False
    ):
        """Decorator to track general performance metrics"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs) -> Any:
                start_time = time.time()
                
                # Extract user ID if tracking user
                user_id = None
                if track_user and args:
                    # Try to extract user ID from common argument patterns
                    if hasattr(args[0], 'effective_user') and args[0].effective_user:
                        user_id = args[0].effective_user.id
                    elif isinstance(args[0], dict) and 'user_id' in args[0]:
                        user_id = args[0]['user_id']
                
                success = False
                
                try:
                    # Execute the function
                    result = await func(*args, **kwargs)
                    success = True
                    return result
                    
                except Exception as e:
                    success = False
                    logger.error(f"Performance tracked operation failed: {operation_name}", extra={
                        "operation": operation_name,
                        "user_id_hash": hash(str(user_id)) if track_user and user_id else None,
                        "error": str(e)
                    })
                    raise
                    
                finally:
                    # Calculate execution time
                    execution_time = (time.time() - start_time) * 1000
                    
                    # Log performance
                    log_performance(
                        operation=operation_name,
                        duration_ms=execution_time,
                        success=success,
                        user_id_hash=hash(str(user_id)) if track_user and user_id else None
                    )
            
            return wrapper
        return decorator
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current telemetry statistics"""
        return {
            "command_stats": self.command_stats.copy(),
            "error_stats": self.error_stats.copy(),
            "performance_stats": self.performance_stats.copy(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def reset_stats(self):
        """Reset all telemetry statistics"""
        self.command_stats.clear()
        self.error_stats.clear()
        self.performance_stats.clear()
        logger.info("Telemetry statistics reset")


# Global telemetry middleware instance
telemetry = TelemetryMiddleware()


# Convenience decorators
def track_command(command_name: Optional[str] = None, track_user: bool = True, track_performance: bool = True):
    """Track Telegram command execution"""
    return telemetry.track_command(command_name, track_user, track_performance)


def track_trade_execution(track_user: bool = True, track_performance: bool = True):
    """Track trade execution"""
    return telemetry.track_trade_execution(track_user, track_performance)


def track_copy_trade(track_user: bool = True, track_performance: bool = True):
    """Track copy trade execution"""
    return telemetry.track_copy_trade(track_user, track_performance)


def track_performance(operation_name: str, track_user: bool = False):
    """Track general performance metrics"""
    return telemetry.track_performance(operation_name, track_user)
