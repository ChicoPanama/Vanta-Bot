from decimal import Decimal

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters

from src.blockchain.wallet_manager import wallet_manager
from src.bot.constants import (
    DEFAULT_LEVERAGE,
    DEFAULT_QUICK_TRADE_SIZE,
    INSUFFICIENT_BALANCE_MESSAGE,
    TRADE_SUCCESS_MESSAGE,
)
from src.bot.keyboards.trading_keyboards import (
    get_crypto_assets_keyboard,
    get_forex_assets_keyboard,
    get_leverage_keyboard,
    get_main_menu_keyboard,
    get_trading_keyboard,
)
from src.bot.middleware.rate_limiter import rate_limiter
from src.bot.middleware.user_middleware import UserMiddleware
from src.config.settings import settings
from src.database.operations import db
from src.services.trading.execution_service import get_execution_service
from src.services.trading.trade_drafts import TradeDraft
from src.utils.logging import get_logger

logger = get_logger(__name__)
user_middleware = UserMiddleware()

# Conversation states
ASSET_SELECTION, SIZE_INPUT, CONFIRM_TRADE = range(3)

# Trading session data
trading_sessions = {}


@rate_limiter.rate_limit(requests=5, per=60)
async def trade_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle trade command/callback"""
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "📊 **Trading Interface**\n\nChoose trading direction and asset category:",
            parse_mode="Markdown",
            reply_markup=get_trading_keyboard(),
        )
    else:
        await update.message.reply_text(
            "📊 **Trading Interface**\n\nChoose trading direction and asset category:",
            parse_mode="Markdown",
            reply_markup=get_trading_keyboard(),
        )


async def trade_direction_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle LONG/SHORT selection"""
    query = update.callback_query
    direction = query.data.split("_")[1]  # trade_long -> long

    user_id = update.effective_user.id
    trading_sessions[user_id] = {"direction": direction.upper()}

    await query.edit_message_text(
        f"📊 **{'🟢 LONG' if direction == 'long' else '🔴 SHORT'} Trade**\n\nSelect asset category:",
        parse_mode="Markdown",
        reply_markup=get_trading_keyboard(),
    )


async def asset_category_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle asset category selection"""
    query = update.callback_query
    category = query.data.split("_")[1]  # category_crypto -> crypto

    keyboard_map = {
        "crypto": get_crypto_assets_keyboard(),
        "forex": get_forex_assets_keyboard(),
        # Add commodities and indices keyboards
    }

    keyboard = keyboard_map.get(category, get_crypto_assets_keyboard())

    await query.edit_message_text(
        f"📊 **Select {category.title()} Asset:**",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


async def asset_selection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle specific asset selection"""
    query = update.callback_query
    asset = query.data.split("_")[1]  # asset_BTC -> BTC

    user_id = update.effective_user.id
    if user_id not in trading_sessions:
        trading_sessions[user_id] = {}

    trading_sessions[user_id]["asset"] = asset

    await query.edit_message_text(
        f"📊 **Trading {asset}**\n\nSelect leverage:",
        parse_mode="Markdown",
        reply_markup=get_leverage_keyboard(),
    )


async def leverage_selection_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Handle leverage selection"""
    query = update.callback_query
    leverage = int(query.data.split("_")[1])  # leverage_10 -> 10

    user_id = update.effective_user.id
    trading_sessions[user_id]["leverage"] = leverage

    await query.edit_message_text(
        f"📊 **Trading Setup**\n"
        f"Asset: {trading_sessions[user_id].get('asset', 'N/A')}\n"
        f"Direction: {trading_sessions[user_id].get('direction', 'N/A')}\n"
        f"Leverage: {leverage}x\n\n"
        f"💰 Enter position size in USDC:",
        parse_mode="Markdown",
    )

    return SIZE_INPUT


async def quick_confirm_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for Quick Trade confirmations.

    Trigger: callback_data matches ^quick_(long|short)$
    Sets default leverage/size and reuses CONFIRM_TRADE state.
    """
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    # Ensure session exists
    if user_id not in trading_sessions:
        trading_sessions[user_id] = {}

    # Asset previously selected from quick_BTC/ETH/... branch
    asset = context.user_data.get("quick_asset", "BTC")
    trading_sessions[user_id]["asset"] = asset

    # Direction from callback
    direction = "LONG" if "quick_long" in query.data else "SHORT"
    trading_sessions[user_id]["direction"] = direction

    # Apply recommended defaults
    trading_sessions[user_id]["leverage"] = DEFAULT_LEVERAGE
    trading_sessions[user_id]["size"] = DEFAULT_QUICK_TRADE_SIZE

    # Build confirm message
    size = trading_sessions[user_id]["size"]
    lev = trading_sessions[user_id]["leverage"]
    notional = float(size) * float(lev)
    confirm_text = (
        f"✅ **Confirm Quick Trade**\n\n"
        f"Asset: {asset}\n"
        f"Direction: {direction}\n"
        f"Size: ${float(size):,.2f} USDC\n"
        f"Leverage: {lev}x\n"
        f"Notional: ${notional:,.2f}\n\n"
        f"Type 'confirm' to execute or 'cancel' to abort."
    )

    await query.edit_message_text(confirm_text, parse_mode="Markdown")
    return CONFIRM_TRADE


async def size_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle position size input"""
    try:
        size = float(update.message.text)
        user_id = update.effective_user.id

        if size < 1:
            await update.message.reply_text("❌ Minimum position size is $1 USDC")
            return SIZE_INPUT

        if size > 100000:
            await update.message.reply_text("❌ Maximum position size is $100,000 USDC")
            return SIZE_INPUT

        trading_sessions[user_id]["size"] = size

        # Calculate notional value
        leverage = trading_sessions[user_id]["leverage"]
        notional = size * leverage

        confirm_text = f"""
✅ **Confirm Trade**

Asset: {trading_sessions[user_id]["asset"]}
Direction: {trading_sessions[user_id]["direction"]}
Size: ${size:,.2f} USDC
Leverage: {leverage}x
Notional: ${notional:,.2f}

Type 'confirm' to execute or 'cancel' to abort.
        """

        await update.message.reply_text(confirm_text, parse_mode="Markdown")
        return CONFIRM_TRADE

    except ValueError:
        await update.message.reply_text("❌ Please enter a valid number")
        return SIZE_INPUT


async def confirm_trade_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle trade confirmation"""
    user_input = update.message.text.lower()
    user_id = update.effective_user.id

    if user_input == "confirm":
        # Execute trade
        await execute_trade(update, user_id)
    elif user_input == "cancel":
        await update.message.reply_text(
            "❌ Trade cancelled.", reply_markup=get_main_menu_keyboard()
        )
    else:
        await update.message.reply_text("Please type 'confirm' or 'cancel'")
        return CONFIRM_TRADE

    # Clean up session
    if user_id in trading_sessions:
        del trading_sessions[user_id]

    return ConversationHandler.END


async def execute_trade(update: Update, user_id: int) -> None:
    """Execute the actual trade"""
    try:
        session = trading_sessions[user_id]

        # Get user from database
        db_user = await db.get_user(user_id)
        if not db_user:
            await update.message.reply_text("❌ User not found")
            return

        # Check wallet balance
        wallet_info = wallet_manager.get_wallet_info(db_user.wallet_address)
        if wallet_info["usdc_balance"] < session["size"]:
            error_msg = INSUFFICIENT_BALANCE_MESSAGE.format(
                required=session["size"], available=wallet_info["usdc_balance"]
            )
            await update.message.reply_text(error_msg)
            return

        # Migrate to unified ExecutionService path (DRY/LIVE aware)
        svc = get_execution_service(settings)
        # Map simple asset (e.g., 'BTC') to a default pair if needed
        pair = session["asset"]
        if "/" not in pair:
            pair = f"{pair}/USD"
        draft = TradeDraft(
            user_id=db_user.id,
            pair=pair,
            side=session["direction"],
            collateral_usdc=Decimal(str(session["size"])),
            leverage=Decimal(str(session["leverage"])),
        )
        ok, msg, res = await svc.execute_open(draft)

        if not ok:
            await update.message.reply_text(
                f"❌ Trade execution failed: {msg}",
                reply_markup=get_main_menu_keyboard(),
            )
            return

        tx_hash = res.get("tx_hash") if isinstance(res, dict) else None

        # Persist a lightweight record for UI (optional; legacy local model)
        try:
            await db.create_position(
                user_id=db_user.id,
                symbol=pair,
                side=session["direction"],
                size=session["size"],
                leverage=session["leverage"],
            )
        except Exception:
            # Non-fatal: execution already succeeded; DB write best-effort
            pass

        success_text = TRADE_SUCCESS_MESSAGE.format(
            tx_hash=(tx_hash or "DRY-MODE"),
            asset=pair,
            direction=session["direction"],
            size=session["size"],
            leverage=session["leverage"],
        )

        await update.message.reply_text(
            success_text, parse_mode="Markdown", reply_markup=get_main_menu_keyboard()
        )

    except Exception as e:
        logger.error(f"Error executing trade: {e}")
        await update.message.reply_text(
            f"❌ Trade execution failed: {str(e)}",
            reply_markup=get_main_menu_keyboard(),
        )


# Conversation handler
trade_conversation = ConversationHandler(
    entry_points=[],  # We'll add this in main.py
    states={
        SIZE_INPUT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, size_input_handler)
        ],
        CONFIRM_TRADE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_trade_handler)
        ],
    },
    fallbacks=[],
)
