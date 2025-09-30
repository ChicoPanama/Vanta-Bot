"""Minimal ABI snippets for Avantis actions (Phase 3)."""

# Minimal ABI for openPosition (replace with exact Avantis contract ABI)
OPEN_POSITION_ABI = {
    "name": "openPosition",
    "type": "function",
    "stateMutability": "nonpayable",
    "inputs": [
        {"name": "marketId", "type": "uint256"},
        {"name": "isLong", "type": "bool"},
        {"name": "sizeUsd", "type": "uint256"},  # 1e6 if protocol uses USDC scale
        {"name": "slippageBps", "type": "uint256"},  # basis points
    ],
    "outputs": [],
}

# Minimal ABI for closePosition
CLOSE_POSITION_ABI = {
    "name": "closePosition",
    "type": "function",
    "stateMutability": "nonpayable",
    "inputs": [
        {"name": "marketId", "type": "uint256"},
        {"name": "reduceUsd", "type": "uint256"},
        {"name": "slippageBps", "type": "uint256"},
    ],
    "outputs": [],
}

# Note: These are simplified ABIs. In production, load from config/abis/current/Trading.json
# or verify against actual Avantis contract ABI
