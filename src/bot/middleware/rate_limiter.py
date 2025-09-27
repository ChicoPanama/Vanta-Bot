"""
Rate Limiting Middleware
Implements rate limiting for bot handlers
"""

import time
from typing import Dict, Optional
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes

from src.utils.logging import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Rate limiting middleware for bot handlers"""
    
    def __init__(self):
        self.requests: Dict[str, Dict[str, float]] = {}
    
    def rate_limit(self, requests: int = 10, per: int = 60, per_user: bool = True):
        """
        Rate limiting decorator
        
        Args:
            requests: Number of requests allowed
            per: Time window in seconds
            per_user: If True, rate limit per user; if False, global rate limit
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
                # Determine rate limit key
                if per_user and update.effective_user:
                    key = f"user_{update.effective_user.id}"
                else:
                    key = "global"
                
                # Check rate limit
                if not self._check_rate_limit(key, requests, per):
                    if update.callback_query:
                        await update.callback_query.answer(
                            "⏰ Rate limit exceeded. Please wait before trying again.",
                            show_alert=True
                        )
                    else:
                        await update.message.reply_text(
                            "⏰ Rate limit exceeded. Please wait before trying again."
                        )
                    return
                
                # Execute handler
                return await func(update, context, *args, **kwargs)
            
            return wrapper
        return decorator
    
    def _check_rate_limit(self, key: str, requests: int, per: int) -> bool:
        """Check if request is within rate limit"""
        now = time.time()
        
        # Initialize key if not exists
        if key not in self.requests:
            self.requests[key] = {}
        
        # Clean old requests
        cutoff = now - per
        self.requests[key] = {
            req_time: req_time for req_time in self.requests[key].values()
            if req_time > cutoff
        }
        
        # Check if under limit
        if len(self.requests[key]) >= requests:
            return False
        
        # Add current request
        self.requests[key][now] = now
        return True


# Global rate limiter instance
rate_limiter = RateLimiter()
