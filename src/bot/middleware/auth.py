"""
Admin Controls & Permissions
Authentication and authorization middleware for Vanta Bot
"""

import os
import functools
import logging
from typing import Set, Optional, Callable, Dict, Any
from telegram import Update
from telegram.ext import ContextTypes

from src.config.settings import settings
from src.utils.logging import get_logger, set_trace_id

log = get_logger(__name__)

# Load admin user IDs from environment
ADMIN_USER_IDS: Set[int] = {
    int(uid.strip()) for uid in os.getenv("ADMIN_USER_IDS", "").split(",") 
    if uid.strip().isdigit()
}

SUPER_ADMIN_IDS: Set[int] = {
    int(uid.strip()) for uid in os.getenv("SUPER_ADMIN_IDS", "").split(",") 
    if uid.strip().isdigit()
}

# Add settings-based admin IDs
if settings.ADMIN_USER_IDS:
    ADMIN_USER_IDS.update(settings.ADMIN_USER_IDS)


class AuthError(Exception):
    """Raised when authentication/authorization fails"""
    pass


def require_admin(func: Callable) -> Callable:
    """Decorator to require admin privileges for a command."""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Set trace ID for request tracking
        trace_id = set_trace_id()
        
        user = update.effective_user
        if not user:
            await update.effective_chat.send_message("Authentication required.")
            return
            
        if user.id not in ADMIN_USER_IDS and user.id not in SUPER_ADMIN_IDS:
            log.warning(
                "Unauthorized admin access attempt",
                extra={
                    'user_id': user.id, 
                    'username': user.username, 
                    'command': func.__name__,
                    'trace_id': trace_id
                }
            )
            await update.effective_chat.send_message(
                "🚫 Admin access required. This incident has been logged."
            )
            return
            
        log.info(
            "Admin command executed",
            extra={
                'user_id': user.id, 
                'username': user.username, 
                'command': func.__name__,
                'trace_id': trace_id
            }
        )
        return await func(update, context)
    return wrapper


def require_super_admin(func: Callable) -> Callable:
    """Decorator to require super admin privileges for sensitive operations."""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        trace_id = set_trace_id()
        
        user = update.effective_user
        if not user:
            await update.effective_chat.send_message("Authentication required.")
            return
            
        if user.id not in SUPER_ADMIN_IDS:
            log.warning(
                "Unauthorized super admin access attempt",
                extra={
                    'user_id': user.id, 
                    'username': user.username, 
                    'command': func.__name__,
                    'trace_id': trace_id
                }
            )
            await update.effective_chat.send_message(
                "🚫 Super admin access required. This incident has been logged."
            )
            return
            
        return await func(update, context)
    return wrapper


async def check_user_permissions(user_id: int) -> Dict[str, Any]:
    """Check user permission levels."""
    return {
        'is_admin': user_id in ADMIN_USER_IDS or user_id in SUPER_ADMIN_IDS,
        'is_super_admin': user_id in SUPER_ADMIN_IDS,
        'can_execute_live': user_id in ADMIN_USER_IDS or user_id in SUPER_ADMIN_IDS,
        'can_modify_settings': user_id in SUPER_ADMIN_IDS,
        'can_emergency_stop': user_id in SUPER_ADMIN_IDS
    }


class ExecutionModeManager:
    """Manage DRY/LIVE execution modes with safety controls."""
    
    def __init__(self):
        self.global_mode = os.getenv("DEFAULT_EXECUTION_MODE", "DRY").upper()
        self.chat_overrides: Dict[int, str] = {}
        
    def get_mode(self, chat_id: int) -> str:
        """Get execution mode for a specific chat."""
        return self.chat_overrides.get(chat_id, self.global_mode)
    
    async def set_chat_mode(self, chat_id: int, mode: str, user_id: int) -> bool:
        """Set execution mode for a chat (admin only)."""
        permissions = await check_user_permissions(user_id)
        if not permissions['can_execute_live']:
            raise AuthError("Insufficient permissions to change execution mode")
            
        mode = mode.upper()
        if mode not in ['DRY', 'LIVE']:
            raise ValueError("Mode must be 'DRY' or 'LIVE'")
            
        self.chat_overrides[chat_id] = mode
        log.info(
            "Execution mode changed",
            extra={
                'chat_id': chat_id, 
                'new_mode': mode, 
                'changed_by': user_id,
                'trace_id': set_trace_id()
            }
        )
        return True
    
    def require_live_confirmation(func: Callable) -> Callable:
        """Decorator that requires confirmation for LIVE mode operations."""
        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            chat_id = update.effective_chat.id
            mode = execution_mode_manager.get_mode(chat_id)
            
            if mode == 'LIVE':
                # Check if user has permission for live trading
                permissions = await check_user_permissions(update.effective_user.id)
                if not permissions['can_execute_live']:
                    await update.effective_chat.send_message(
                        "🚫 Live trading requires admin privileges."
                    )
                    return
                
                # Add confirmation step for live trading
                if not context.user_data.get('confirmed_live_trade', False):
                    await update.effective_chat.send_message(
                        "⚠️ **LIVE TRADING MODE ACTIVE** ⚠️\n\n"
                        "This will execute real trades on Avantis Protocol.\n"
                        "Type 'CONFIRM' to proceed or 'CANCEL' to abort."
                    )
                    
                    # Set up confirmation handler
                    context.user_data['pending_live_trade'] = func
                    return
            
            return await func(update, context)
        return wrapper


def check_emergency_stop() -> bool:
    """Check if emergency stop is active."""
    return (
        os.getenv("EMERGENCY_STOP", "false").lower() == "true" or
        settings.EMERGENCY_STOP
    )


def check_maintenance_mode() -> bool:
    """Check if maintenance mode is active."""
    return (
        os.getenv("MAINTENANCE_MODE", "false").lower() == "true" or
        settings.MAINTENANCE_MODE
    )


def require_not_emergency_stopped(func: Callable) -> Callable:
    """Decorator to prevent execution during emergency stop."""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if check_emergency_stop():
            await update.effective_chat.send_message(
                "🚨 **EMERGENCY STOP ACTIVE** 🚨\n\n"
                "All trading operations have been halted for safety.\n"
                "Contact administrators for assistance."
            )
            return
        
        if check_maintenance_mode():
            await update.effective_chat.send_message(
                "🔧 **MAINTENANCE MODE** 🔧\n\n"
                "The bot is currently under maintenance.\n"
                "Please try again later."
            )
            return
            
        return await func(update, context)
    return wrapper


async def handle_live_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle live trading confirmation responses."""
    text = update.message.text.upper().strip()
    
    if text == 'CONFIRM':
        context.user_data['confirmed_live_trade'] = True
        pending_func = context.user_data.get('pending_live_trade')
        
        if pending_func:
            del context.user_data['pending_live_trade']
            await pending_func(update, context)
        else:
            await update.effective_chat.send_message("No pending trade to confirm.")
            
    elif text == 'CANCEL':
        context.user_data.pop('pending_live_trade', None)
        context.user_data.pop('confirmed_live_trade', None)
        await update.effective_chat.send_message("Trade cancelled.")
        
    else:
        await update.effective_chat.send_message(
            "Please type 'CONFIRM' to proceed or 'CANCEL' to abort."
        )


# Global execution mode manager instance
execution_mode_manager = ExecutionModeManager()
