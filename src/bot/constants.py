"""
Bot Constants
Centralized constants for the bot application
"""

# Message templates
WELCOME_MESSAGE = """
🚀 **Welcome to Vanta Bot!**

Your trading wallet has been created:
📍 **Address:** `{wallet_address}`

💡 **Choose your trading experience level:**
• 🟢 **Simple Trader** - Easy one-click trading
• 🔴 **Advanced Trader** - Professional tools

🛡️ **Security:** Your private keys are encrypted and stored securely.
⚡ **Zero Fees:** Pay fees only on profitable trades!
"""

USER_NOT_FOUND_MESSAGE = "❌ User not found. Please /start first."

# Trading constants
DEFAULT_LEVERAGE = 10
DEFAULT_QUICK_TRADE_SIZE = 100
MAX_LEVERAGE = 500
MIN_POSITION_SIZE = 1
MAX_POSITION_SIZE = 100000

# Asset categories
CRYPTO_ASSETS = ["BTC", "ETH", "SOL", "AVAX", "MATIC", "LINK"]
FOREX_ASSETS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD"]

# Leverage options
LEVERAGE_OPTIONS = [1, 2, 5, 10, 20, 50, 100, 200, 500]

# Error messages
INSUFFICIENT_BALANCE_MESSAGE = (
    "❌ Insufficient USDC balance. Need ${required}, have ${available:.2f}"
)
TRADE_SUCCESS_MESSAGE = """
✅ **Trade Executed Successfully!**

Transaction Hash: `{tx_hash}`

Position Details:
• Asset: {asset}
• Direction: {direction}
• Size: ${size:,.2f} USDC
• Leverage: {leverage}x

View your positions with /positions
"""

# Portfolio messages
NO_POSITIONS_MESSAGE = """
📈 **Your Positions**

No open positions found.

Start trading with the Trade button!
"""

NO_ORDERS_MESSAGE = """
📋 **Your Orders**

No pending orders found.

Create orders through the trading interface!
"""

# Settings categories
SETTINGS_CATEGORIES = ["notifications", "risk", "trading", "security", "about"]

# User interface types
USER_INTERFACE_TYPES = {"simple": "Simple Trader", "advanced": "Advanced Trader"}
