"""Oracle providers package."""

from .chainlink import ChainlinkOracle
from .pyth import PythOracle

__all__ = ["PythOracle", "ChainlinkOracle"]
