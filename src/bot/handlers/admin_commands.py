"""
Admin commands for production management
"""
import os
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from loguru import logger

from src.services.copy_trading.execution_mode import execution_manager, ExecutionMode

# Admin user IDs (set via environment)
ADMIN_USER_IDS = set(int(uid) for uid in os.getenv("ADMIN_USER_IDS", "").split(",") if uid.strip())

def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in ADMIN_USER_IDS

async def cmd_copy_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle copy execution mode: /copy mode DRY|LIVE"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin access required")
        return
        
    args = context.args
    if len(args) != 1:
        await update.message.reply_text(
            "Usage: `/copy mode DRY|LIVE`\n\n"
            "Current mode: `{}`\n"
            "Emergency stop: `{}`".format(
                execution_manager.mode.value,
                execution_manager.is_emergency_stopped
            ),
            parse_mode='Markdown'
        )
        return
        
    mode_str = args[0].upper()
    try:
        new_mode = ExecutionMode(mode_str)
        old_mode = execution_manager.mode
        execution_manager.set_mode(new_mode)
        
        await update.message.reply_text(
            f"✅ Copy execution mode changed: `{old_mode.value}` → `{new_mode.value}`",
            parse_mode='Markdown'
        )
        
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid mode. Use `DRY` or `LIVE`",
            parse_mode='Markdown'
        )

async def cmd_emergency_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Emergency stop all copy execution: /emergency stop|start"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin access required")
        return
        
    args = context.args
    if len(args) != 1:
        await update.message.reply_text(
            "Usage: `/emergency stop|start`\n\n"
            "Current status: `{}`".format(
                "STOPPED" if execution_manager.is_emergency_stopped else "RUNNING"
            ),
            parse_mode='Markdown'
        )
        return
        
    action = args[0].lower()
    if action == "stop":
        execution_manager.set_emergency_stop(True)
        await update.message.reply_text(
            "🚨 **EMERGENCY STOP ACTIVATED**\n\n"
            "All copy execution has been disabled.",
            parse_mode='Markdown'
        )
    elif action == "start":
        execution_manager.set_emergency_stop(False)
        await update.message.reply_text(
            "✅ **Emergency stop deactivated**\n\n"
            "Copy execution can resume (subject to execution mode).",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "❌ Invalid action. Use `stop` or `start`",
            parse_mode='Markdown'
        )

async def cmd_system_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show system status: /status admin"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin access required")
        return
        
    context_data = execution_manager.get_execution_context()
    
    status_text = (
        "🔧 **System Status**\n\n"
        f"**Execution Mode:** `{context_data['mode']}`\n"
        f"**Emergency Stop:** `{'ACTIVE' if context_data['emergency_stop'] else 'INACTIVE'}`\n"
        f"**Can Execute:** `{'YES' if context_data['can_execute'] else 'NO'}`\n\n"
        "**Commands:**\n"
        "• `/copy mode DRY|LIVE` - Toggle execution mode\n"
        "• `/emergency stop|start` - Emergency stop control"
    )
    
    await update.message.reply_text(status_text, parse_mode='Markdown')

# Export handlers for registration
admin_handlers = [
    CommandHandler("copy", cmd_copy_mode),
    CommandHandler("emergency", cmd_emergency_stop),
    CommandHandler("status", cmd_system_status),
]
