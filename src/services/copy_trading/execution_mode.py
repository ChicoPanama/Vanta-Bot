"""
Copy execution mode management for safe testing and production rollouts
"""
import os
from enum import Enum
from typing import Dict, Any
from loguru import logger

class ExecutionMode(Enum):
    DRY = "DRY"
    LIVE = "LIVE"

class ExecutionModeManager:
    """Manages copy execution mode with runtime toggles"""
    
    def __init__(self):
        self._mode = ExecutionMode(os.getenv("COPY_EXECUTION_MODE", "DRY"))
        self._emergency_stop = os.getenv("EMERGENCY_STOP", "false").lower() == "true"
        
    @property
    def mode(self) -> ExecutionMode:
        """Get current execution mode"""
        return self._mode
        
    @property
    def is_dry_run(self) -> bool:
        """Check if currently in dry-run mode"""
        return self._mode == ExecutionMode.DRY
        
    @property
    def is_emergency_stopped(self) -> bool:
        """Check if emergency stop is active"""
        return self._emergency_stop
        
    def set_mode(self, mode: ExecutionMode) -> None:
        """Set execution mode (for runtime toggling)"""
        old_mode = self._mode
        self._mode = mode
        logger.info("Copy execution mode changed: {} -> {}", old_mode.value, mode.value)
        
    def set_emergency_stop(self, stop: bool) -> None:
        """Set emergency stop (for quick rollback)"""
        self._emergency_stop = stop
        logger.warning("Emergency stop {}: all copy execution disabled", 
                      "ACTIVATED" if stop else "DEACTIVATED")
        
    def can_execute(self) -> bool:
        """Check if copy execution is allowed"""
        if self._emergency_stop:
            logger.debug("Copy execution blocked: emergency stop active")
            return False
        return True
        
    def get_execution_context(self) -> Dict[str, Any]:
        """Get execution context for logging/auditing"""
        return {
            "mode": self._mode.value,
            "emergency_stop": self._emergency_stop,
            "can_execute": self.can_execute()
        }

# Global instance
execution_manager = ExecutionModeManager()
