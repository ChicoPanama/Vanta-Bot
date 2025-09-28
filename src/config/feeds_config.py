"""Centralized feeds configuration loader."""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

from src.utils.logging import get_logger

logger = get_logger(__name__)


class FeedsConfig:
    """Centralized feeds configuration manager."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize feeds configuration."""
        if config_path is None:
            # Default to config/feeds.json in project root
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "feeds.json"
        
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from JSON file."""
        try:
            if not self.config_path.exists():
                logger.warning(f"Feeds config file not found: {self.config_path}")
                return
            
            with open(self.config_path, 'r') as f:
                self._config = json.load(f)
            
            logger.info(f"Loaded feeds configuration from {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to load feeds configuration: {e}")
            self._config = {}
    
    def get_pyth_config(self) -> Dict[str, Any]:
        """Get Pyth oracle configuration."""
        return self._config.get("pyth", {})
    
    def get_chainlink_config(self) -> Dict[str, Any]:
        """Get Chainlink oracle configuration."""
        return self._config.get("chainlink", {})
    
    def get_oracle_config(self) -> Dict[str, Any]:
        """Get general oracle configuration."""
        return self._config.get("oracle", {})
    
    def get_execution_mode_config(self) -> Dict[str, Any]:
        """Get execution mode configuration."""
        return self._config.get("execution_mode", {})
    
    def get_chainlink_feeds(self) -> Dict[str, str]:
        """Get Chainlink feed addresses."""
        chainlink_config = self.get_chainlink_config()
        base_network = chainlink_config.get("base_network", {})
        return base_network.get("feeds", {})
    
    def get_chainlink_sanity_ranges(self) -> Dict[str, Dict[str, float]]:
        """Get Chainlink sanity price ranges."""
        chainlink_config = self.get_chainlink_config()
        base_network = chainlink_config.get("base_network", {})
        return base_network.get("sanity_ranges", {})
    
    def get_pyth_symbols(self) -> Dict[str, str]:
        """Get Pyth symbol mappings."""
        pyth_config = self.get_pyth_config()
        return pyth_config.get("symbols", {})
    
    def get_oracle_thresholds(self) -> Dict[str, int]:
        """Get oracle validation thresholds."""
        oracle_config = self.get_oracle_config()
        return {
            "max_deviation_bps": oracle_config.get("max_deviation_bps", 50),
            "max_age_seconds": oracle_config.get("max_age_seconds", 30)
        }
    
    def get_validation_config(self) -> Dict[str, Any]:
        """Get oracle validation configuration."""
        oracle_config = self.get_oracle_config()
        return oracle_config.get("validation", {})
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get configuration metadata."""
        return self._config.get("metadata", {})
    
    def reload(self) -> None:
        """Reload configuration from file."""
        self._load_config()
    
    def is_available(self) -> bool:
        """Check if configuration is available."""
        return bool(self._config)


# Global instance
feeds_config = FeedsConfig()


def get_feeds_config() -> FeedsConfig:
    """Get the global feeds configuration instance."""
    return feeds_config
