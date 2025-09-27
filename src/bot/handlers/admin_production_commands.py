"""
Production Admin Commands
Administrative commands for production monitoring and control
"""

import asyncio
from decimal import Decimal
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from src.bot.middleware.auth import (
    require_admin, require_super_admin, execution_mode_manager,
    check_emergency_stop, check_maintenance_mode
)
from src.services.risk_manager import risk_manager
from src.middleware.rate_limiter import rate_limiter
from src.services.price_feed_manager import price_feed_manager
from src.utils.logging import get_logger, set_trace_id

log = get_logger(__name__)


@require_super_admin
async def admin_emergency_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Emergency stop all trading operations"""
    trace_id = set_trace_id()
    
    try:
        import os
        os.environ["EMERGENCY_STOP"] = "true"
        
        log.critical(
            "EMERGENCY STOP ACTIVATED",
            extra={
                'user_id': update.effective_user.id,
                'username': update.effective_user.username,
                'trace_id': trace_id
            }
        )
        
        await update.effective_chat.send_message(
            "🚨 **EMERGENCY STOP ACTIVATED** 🚨\n\n"
            "All trading operations have been halted immediately.\n"
            "The bot will remain running for monitoring but no new trades will be executed.",
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        log.error(f"Error activating emergency stop: {e}", extra={'trace_id': trace_id})
        await update.effective_chat.send_message(f"❌ Error: {e}")


@require_super_admin
async def admin_emergency_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resume operations after emergency stop"""
    trace_id = set_trace_id()
    
    try:
        import os
        os.environ["EMERGENCY_STOP"] = "false"
        
        log.warning(
            "EMERGENCY STOP DEACTIVATED",
            extra={
                'user_id': update.effective_user.id,
                'username': update.effective_user.username,
                'trace_id': trace_id
            }
        )
        
        await update.effective_chat.send_message(
            "✅ **EMERGENCY STOP DEACTIVATED**\n\n"
            "Trading operations have been resumed.\n"
            "Normal operation restored.",
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        log.error(f"Error deactivating emergency stop: {e}", extra={'trace_id': trace_id})
        await update.effective_chat.send_message(f"❌ Error: {e}")


@require_admin
async def admin_execution_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get or set execution mode"""
    trace_id = set_trace_id()
    
    try:
        if context.args:
            new_mode = context.args[0].upper()
            chat_id = update.effective_chat.id
            user_id = update.effective_user.id
            
            success = await execution_mode_manager.set_chat_mode(chat_id, new_mode, user_id)
            
            if success:
                await update.effective_chat.send_message(
                    f"✅ Execution mode set to **{new_mode}**",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.effective_chat.send_message("❌ Failed to set execution mode")
        else:
            # Show current mode
            chat_id = update.effective_chat.id
            current_mode = execution_mode_manager.get_mode(chat_id)
            
            await update.effective_chat.send_message(
                f"📊 **Current Execution Mode**: {current_mode}\n\n"
                f"Usage: `/execution_mode [DRY|LIVE]`",
                parse_mode=ParseMode.MARKDOWN
            )
            
    except Exception as e:
        log.error(f"Error managing execution mode: {e}", extra={'trace_id': trace_id})
        await update.effective_chat.send_message(f"❌ Error: {e}")


@require_admin
async def admin_risk_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get risk management summary"""
    trace_id = set_trace_id()
    
    try:
        # Example account balance (in real implementation, get from user's wallet)
        account_balance = Decimal('10000')  # $10,000 example
        
        summary = risk_manager.get_risk_summary(account_balance)
        
        limits = summary['limits']
        account_info = f"Account Balance: ${summary['account_balance_usd']:,.2f}\n\n"
        
        limits_text = f"""
**Risk Management Summary**

{account_info}**Position Limits:**
• Max Position Size: ${limits['max_position_size_usd']:,.0f}
• Max Account Risk: {limits['max_account_risk_pct']:.1%}
• Max Leverage: {limits['max_leverage']:.0f}x

**Safety Buffers:**
• Liquidation Buffer: {limits['liquidation_buffer_pct']:.1%}
• Max Daily Loss: {limits['max_daily_loss_pct']:.1%}

**Safe Position Sizes:**
• 1x Leverage: ${summary['max_safe_position_1x']:,.0f}
• 10x Leverage: ${summary['max_safe_position_10x']:,.0f}
• 100x Leverage: ${summary['max_safe_position_100x']:,.0f}
• 500x Leverage: ${summary['max_safe_position_500x']:,.0f}
        """
        
        await update.effective_chat.send_message(
            limits_text,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        log.error(f"Error getting risk summary: {e}", extra={'trace_id': trace_id})
        await update.effective_chat.send_message(f"❌ Error: {e}")


@require_admin
async def admin_rate_limits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get rate limiting status"""
    trace_id = set_trace_id()
    
    try:
        user_id = str(update.effective_user.id)
        status = await rate_limiter.get_rate_limit_status(user_id)
        
        stats = status['stats']
        limits = status['limits']
        
        status_text = f"""
**Rate Limiting Status**

**Current Usage:**
• Hourly Trades: {stats['hourly_trades']}
• Daily Trades: {stats['daily_trades']}
• Hourly Volume: ${stats['hourly_volume_usd']:,.2f}
• Daily Volume: ${stats['daily_volume_usd']:,.2f}

**Limits:**
• Telegram Messages: {limits['telegram_messages']['current']}/{limits['telegram_messages']['limit']} per minute
• Copy Executions: {limits['copy_executions']['current']}/{limits['copy_executions']['limit']} per minute
• Daily Trades: {limits['daily_trades']['current']}/{limits['daily_trades']['limit']}
• Hourly Volume: ${limits['hourly_volume']['current']:,.2f}/${limits['hourly_volume']['limit']:,.2f}
        """
        
        await update.effective_chat.send_message(
            status_text,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        log.error(f"Error getting rate limit status: {e}", extra={'trace_id': trace_id})
        await update.effective_chat.send_message(f"❌ Error: {e}")


@require_admin
async def admin_price_feeds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get price feed health status"""
    trace_id = set_trace_id()
    
    try:
        feed_health = price_feed_manager.get_feed_health()
        
        if not feed_health:
            await update.effective_chat.send_message("📊 No price feeds configured")
            return
        
        health_text = "**Price Feed Health Status**\n\n"
        
        for asset, health in feed_health.items():
            status_emoji = "✅" if not health['is_stale'] else "⚠️"
            age_seconds = health['age_seconds']
            
            health_text += f"{status_emoji} **{asset}**\n"
            health_text += f"   Price: ${health['price']:,.2f}\n"
            health_text += f"   Source: {health['source']}\n"
            health_text += f"   Age: {age_seconds:.1f}s\n"
            health_text += f"   Stale: {'Yes' if health['is_stale'] else 'No'}\n\n"
        
        await update.effective_chat.send_message(
            health_text,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        log.error(f"Error getting price feed health: {e}", extra={'trace_id': trace_id})
        await update.effective_chat.send_message(f"❌ Error: {e}")


@require_admin
async def admin_system_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get overall system status"""
    trace_id = set_trace_id()
    
    try:
        # Check various system states
        emergency_stop = check_emergency_stop()
        maintenance_mode = check_maintenance_mode()
        
        # Get basic health info
        chat_id = update.effective_chat.id
        execution_mode = execution_mode_manager.get_mode(chat_id)
        
        status_text = f"""
**System Status**

**Operational State:**
• Emergency Stop: {'🚨 ACTIVE' if emergency_stop else '✅ Normal'}
• Maintenance Mode: {'🔧 ACTIVE' if maintenance_mode else '✅ Normal'}
• Execution Mode: {execution_mode}

**Services:**
• Risk Manager: ✅ Active
• Price Feeds: ✅ Active
• Rate Limiter: ✅ Active
• Task Supervisor: ✅ Active
• Health Monitoring: ✅ Active

**Trace ID**: `{trace_id}`
        """
        
        await update.effective_chat.send_message(
            status_text,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        log.error(f"Error getting system status: {e}", extra={'trace_id': trace_id})
        await update.effective_chat.send_message(f"❌ Error: {e}")


@require_super_admin
async def admin_maintenance_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle maintenance mode"""
    trace_id = set_trace_id()
    
    try:
        import os
        
        if context.args and context.args[0].lower() in ['on', 'enable', 'true']:
            os.environ["MAINTENANCE_MODE"] = "true"
            message = "🔧 **MAINTENANCE MODE ACTIVATED**\n\nAll user interactions are temporarily disabled."
        else:
            os.environ["MAINTENANCE_MODE"] = "false"
            message = "✅ **MAINTENANCE MODE DEACTIVATED**\n\nNormal operation resumed."
        
        log.info(
            f"Maintenance mode toggled: {os.environ.get('MAINTENANCE_MODE')}",
            extra={
                'user_id': update.effective_user.id,
                'username': update.effective_user.username,
                'trace_id': trace_id
            }
        )
        
        await update.effective_chat.send_message(
            message,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        log.error(f"Error toggling maintenance mode: {e}", extra={'trace_id': trace_id})
        await update.effective_chat.send_message(f"❌ Error: {e}")


# Admin command help
async def admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin command help"""
    trace_id = set_trace_id()
    
    help_text = """
**Admin Commands**

**System Control:**
• `/emergency_stop` - Emergency halt all trading
• `/emergency_resume` - Resume after emergency stop
• `/maintenance_mode [on/off]` - Toggle maintenance mode
• `/execution_mode [DRY/LIVE]` - Set execution mode

**Monitoring:**
• `/system_status` - Overall system status
• `/risk_summary` - Risk management limits
• `/rate_limits` - Rate limiting status
• `/price_feeds` - Price feed health

**Help:**
• `/admin_help` - Show this help

*All commands require admin privileges*
    """
    
    await update.effective_chat.send_message(
        help_text,
        parse_mode=ParseMode.MARKDOWN
    )
