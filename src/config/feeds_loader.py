"""Feed configuration loader."""

import json
from pathlib import Path
from typing import Dict

_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "feeds.json"


def load_chainlink_feeds() -> dict[str, str]:
    """Load Chainlink feed addresses from config.

    Returns:
        Dict mapping symbol to feed address (e.g., {"BTC": "0x64c9..."})
    """
    with open(_CONFIG_PATH) as f:
        config = json.load(f)

    return config.get("chainlink", {}).get("base_network", {}).get("feeds", {})


def load_pyth_symbols() -> dict[str, str]:
    """Load Pyth price feed IDs from config.

    Returns:
        Dict mapping symbol to Pyth price ID (e.g., {"BTC": "0xe62df6..."})
    """
    with open(_CONFIG_PATH) as f:
        config = json.load(f)

    return config.get("pyth", {}).get("symbols", {})
