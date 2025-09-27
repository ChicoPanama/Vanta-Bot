from decimal import Decimal, ROUND_DOWN
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from src.services.risk_calculator import risk_calculator, RiskLevel
from src.config.settings import settings
from src.bot.middleware.user_middleware import UserMiddleware
from src.blockchain.wallet_manager import wallet_manager
from src.database.operations import db

logger = __import__('src.utils.logging', fromlist=['get_logger']).get_logger(__name__)
user_middleware = UserMiddleware()

# Helpers
async def _get_account_balance_usd(user_id: int) -> Decimal:
    """Get user's account balance in USD"""
    try:
        db_user = db.get_user(user_id)
        if not db_user:
            return Decimal("10000")  # Default for demo
        
        wallet_info = wallet_manager.get_wallet_info(db_user.wallet_address)
        return Decimal(str(wallet_info.get('usdc_balance', 10000)))
    except Exception as e:
        logger.warning(f"Could not get balance for user {user_id}: {e}")
        return Decimal("10000")  # Default fallback

def _fmt_usd(x: Decimal) -> str:
    """Format USD amount"""
    return f"${x:,.2f}"

def _emoji_for(level: str) -> str:
    """Get emoji for risk level"""
    emojis = {
        "conservative": "🟢",
        "moderate": "🟡", 
        "aggressive": "🟠",
        "extreme": "🔴"
    }
    return emojis.get(level, "🟡")

@user_middleware.require_user
async def cmd_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Usage: /analyze <ASSET> <SIZE_USD> <LEVERAGE>  (education only)"""
    if not settings.RISK_EDUCATION_ENABLED:
        await update.effective_message.reply_text(
            "📊 Risk education is currently disabled.",
            parse_mode="Markdown"
        )
        return

    args = context.args or []
    if len(args) < 3:
        await update.effective_message.reply_text(
            "📊 *Analyzer*\n\nUsage: `/analyze <ASSET> <SIZE_USD> <LEVERAGE>`\n\n"
            "Example: `/analyze ETH 1000 20`\n\n"
            "_This analyzes risk scenarios without executing any trades._",
            parse_mode="Markdown",
        )
        return

    try:
        asset = args[0].upper()
        size = Decimal(args[1])
        lev = Decimal(args[2])
        bal = await _get_account_balance_usd(update.effective_user.id)

        edu = await risk_calculator.analyze(
            position_size_usd=size,
            leverage=lev,
            account_balance_usd=bal,
            asset=asset,
            protocol_max_leverage=settings.RISK_PROTOCOL_MAX_LEVERAGE,
        )

        sc = edu["scenarios"]
        msg = (
            f"📊 *{asset}* Risk Analysis\n"
            f"Size: {_fmt_usd(size)} | {lev}x ({edu['leverage_category']})\n\n"
            f"💰 **Requirements:**\n"
            f"• Margin required: {_fmt_usd(edu['margin_required'])}\n"
            f"• Liquidation distance: {edu['liq_distance_pct']:.2%}\n\n"
            f"🎯 **Risk Assessment:**\n"
            f"• Risk level: {_emoji_for(edu['risk_level'])} {edu['risk_level'].title()}\n"
            f"• Position quality: {edu['position_quality']['rating']} ({edu['position_quality']['score']}/100)\n\n"
            f"📈 **Scenario Analysis:**\n"
            f"• 0.5% move: -{sc['move_0_5']['account_impact_pct']:.1%} equity\n"
            f"• 1.0% move: -{sc['move_1_0']['account_impact_pct']:.1%}\n"
            f"• 2.0% move: -{sc['stress_move']['account_impact_pct']:.1%}\n"
            f"• 5.0% move: -{sc['crash_5']['account_impact_pct']:.1%}\n"
            f"• 10% move: -{sc['black_swan_10']['account_impact_pct']:.1%}\n\n"
            f"_Your money, your choice. This is education, not restriction._"
        )

        # Show warnings if any
        if edu["educational_warnings"]:
            msg += "\n\n⚠️ *Educational Notes:*\n"
            for w in edu["educational_warnings"]:
                emoji = "🚨" if w["severity"] == "high" else "⚠️"
                msg += f"{emoji} {w['title']}: {w['message']}\n"

        await update.effective_message.reply_text(msg, parse_mode="Markdown")

    except ValueError as e:
        await update.effective_message.reply_text(
            f"❌ Error: {str(e)}\n\nPlease check your inputs and try again.",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error in analyze command: {e}")
        await update.effective_message.reply_text(
            "❌ An error occurred while analyzing. Please try again.",
            parse_mode="Markdown"
        )

@user_middleware.require_user
async def cmd_calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Usage: /calc <ASSET> <LEVERAGE> [risk_pct]  — suggest sizes"""
    if not settings.RISK_EDUCATION_ENABLED:
        await update.effective_message.reply_text(
            "🧮 Risk education is currently disabled.",
            parse_mode="Markdown"
        )
        return

    args = context.args or []
    if len(args) < 2:
        await update.effective_message.reply_text(
            "🧮 *Position Calculator*\n\nUsage: `/calc <ASSET> <LEVERAGE> [risk_pct]`\n\n"
            "Examples:\n"
            "• `/calc ETH 20` - Show all risk tiers\n"
            "• `/calc ETH 20 5` - Show size for 5% risk\n\n"
            "_This suggests position sizes based on risk tolerance._",
            parse_mode="Markdown",
        )
        return

    try:
        asset = args[0].upper()
        lev = Decimal(args[1])
        risk_pct = Decimal(args[2]) / Decimal(100) if len(args) > 2 else None

        bal = await _get_account_balance_usd(update.effective_user.id)
        
        # Suggest sizes using the same assumptions as the calculator
        def size_for(rpct: Decimal) -> Decimal:
            max_loss = bal * rpct
            return (max_loss / Decimal("0.02")).quantize(Decimal("0.01"), rounding=ROUND_DOWN)

        if risk_pct:
            size = size_for(risk_pct)
            edu = await risk_calculator.analyze(
                position_size_usd=size, 
                leverage=lev, 
                account_balance_usd=bal, 
                asset=asset
            )
            msg = (
                f"🧮 *{asset}* at {lev}x\n"
                f"Target risk: {risk_pct:.1%} of equity\n\n"
                f"💰 **Suggested size:** {_fmt_usd(size)}\n"
                f"• Margin required: {_fmt_usd(edu['margin_required'])}\n"
                f"• Position quality: {edu['position_quality']['rating']} ({edu['position_quality']['score']}/100)\n\n"
                f"_This assumes a 2% adverse move scenario._"
            )
        else:
            cons = size_for(Decimal("0.02"))
            mod = size_for(Decimal("0.05"))
            agg = size_for(Decimal("0.10"))
            msg = (
                f"🧮 *{asset}* at {lev}x — Suggested Sizes\n\n"
                f"🟢 **Conservative (2% risk):** {_fmt_usd(cons)}\n"
                f"🟡 **Moderate (5% risk):** {_fmt_usd(mod)}\n"
                f"🟠 **Aggressive (10% risk):** {_fmt_usd(agg)}\n\n"
                f"_Based on {_fmt_usd(bal)} account balance._"
            )
            
        await update.effective_message.reply_text(msg, parse_mode="Markdown")

    except ValueError as e:
        await update.effective_message.reply_text(
            f"❌ Error: {str(e)}\n\nPlease check your inputs and try again.",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error in calc command: {e}")
        await update.effective_message.reply_text(
            "❌ An error occurred while calculating. Please try again.",
            parse_mode="Markdown"
        )

def register_risk_edu_handlers(dispatcher):
    """Register risk education handlers"""
    dispatcher.add_handler(CommandHandler("analyze", cmd_analyze))
    dispatcher.add_handler(CommandHandler("calc", cmd_calc))
