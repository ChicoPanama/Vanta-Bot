"""Pydantic schemas for bot command validation."""

from pydantic import BaseModel, Field, validator
from decimal import Decimal
from typing import Optional, Literal
from src.config.settings import settings


class OpenPositionCommand(BaseModel):
    """Schema for /open command."""
    market: str = Field(..., description="Market symbol (e.g., BTC, ETH)")
    size: Decimal = Field(..., gt=0, description="Position size in USDC")
    leverage: Decimal = Field(..., gt=0, le=settings.MAX_LEVERAGE, description="Leverage multiplier")
    side: Literal["long", "short"] = Field(..., description="Position side")
    
    @validator('market')
    def validate_market(cls, v):
        if not v or len(v) < 2:
            raise ValueError('Market must be at least 2 characters')
        return v.upper()
    
    @validator('size')
    def validate_size(cls, v):
        if v < settings.MIN_POSITION_SIZE:
            raise ValueError(f'Size must be at least {settings.MIN_POSITION_SIZE}')
        if v > settings.MAX_POSITION_SIZE:
            raise ValueError(f'Size must be at most {settings.MAX_POSITION_SIZE}')
        return v


class ClosePositionCommand(BaseModel):
    """Schema for /close command."""
    position_id: int = Field(..., gt=0, description="Position ID to close")
    
    @validator('position_id')
    def validate_position_id(cls, v):
        if v <= 0:
            raise ValueError('Position ID must be positive')
        return v


class StatusCommand(BaseModel):
    """Schema for /status command."""
    detailed: bool = Field(False, description="Include detailed information")


class BalanceCommand(BaseModel):
    """Schema for /balance command."""
    currency: Optional[str] = Field(None, description="Currency to check (ETH, USDC)")
    
    @validator('currency')
    def validate_currency(cls, v):
        if v is not None:
            v = v.upper()
            if v not in ['ETH', 'USDC']:
                raise ValueError('Currency must be ETH or USDC')
        return v


class PositionsCommand(BaseModel):
    """Schema for /positions command."""
    status: Optional[Literal["open", "closed", "all"]] = Field("open", description="Position status filter")
    limit: int = Field(10, ge=1, le=50, description="Maximum number of positions to show")


class AdminCommand(BaseModel):
    """Schema for /admin command."""
    action: Literal["status", "users", "emergency_stop", "maintenance"] = Field(..., description="Admin action")
    user_id: Optional[int] = Field(None, description="Target user ID for user actions")
    
    @validator('user_id')
    def validate_user_id(cls, v, values):
        if 'action' in values and values['action'] in ['users'] and v is None:
            raise ValueError('user_id is required for user actions')
        return v


class EmergencyStopCommand(BaseModel):
    """Schema for emergency stop command."""
    reason: str = Field(..., min_length=1, max_length=200, description="Reason for emergency stop")
    scope: Literal["all", "trading", "copy_trading"] = Field("all", description="Scope of emergency stop")


class MaintenanceCommand(BaseModel):
    """Schema for maintenance command."""
    action: Literal["start", "stop", "status"] = Field(..., description="Maintenance action")
    message: Optional[str] = Field(None, max_length=500, description="Maintenance message")


class UserManagementCommand(BaseModel):
    """Schema for user management commands."""
    action: Literal["add_admin", "remove_admin", "add_super_admin", "remove_super_admin", "list"] = Field(..., description="User management action")
    user_id: Optional[int] = Field(None, description="Target user ID")
    
    @validator('user_id')
    def validate_user_id(cls, v, values):
        if 'action' in values and values['action'] != 'list' and v is None:
            raise ValueError('user_id is required for user management actions')
        return v


class MetricsCommand(BaseModel):
    """Schema for /metrics command."""
    metric_type: Literal["system", "trading", "users", "all"] = Field("all", description="Type of metrics to show")
    time_range: Literal["1h", "24h", "7d", "30d"] = Field("24h", description="Time range for metrics")


class HelpCommand(BaseModel):
    """Schema for /help command."""
    command: Optional[str] = Field(None, description="Specific command to get help for")
    
    @validator('command')
    def validate_command(cls, v):
        if v is not None:
            v = v.lower().strip('/')
            valid_commands = [
                'start', 'help', 'status', 'open', 'close', 'positions', 
                'balance', 'admin', 'emergency_stop', 'maintenance', 'metrics'
            ]
            if v not in valid_commands:
                raise ValueError(f'Unknown command: {v}. Valid commands: {", ".join(valid_commands)}')
        return v


# Command registry for validation
COMMAND_SCHEMAS = {
    'open': OpenPositionCommand,
    'close': ClosePositionCommand,
    'status': StatusCommand,
    'balance': BalanceCommand,
    'positions': PositionsCommand,
    'admin': AdminCommand,
    'emergency_stop': EmergencyStopCommand,
    'maintenance': MaintenanceCommand,
    'user_management': UserManagementCommand,
    'metrics': MetricsCommand,
    'help': HelpCommand,
}


def validate_command(command: str, data: dict) -> BaseModel:
    """Validate command data against schema.
    
    Args:
        command: Command name
        data: Command data
        
    Returns:
        Validated command object
        
    Raises:
        ValueError: If validation fails
    """
    if command not in COMMAND_SCHEMAS:
        raise ValueError(f'Unknown command: {command}')
    
    schema_class = COMMAND_SCHEMAS[command]
    try:
        return schema_class(**data)
    except Exception as e:
        raise ValueError(f'Command validation failed: {e}')


def get_command_help(command: str) -> str:
    """Get help text for command.
    
    Args:
        command: Command name
        
    Returns:
        Help text
    """
    help_texts = {
        'open': 'Open a new position: /open <market> <size> <leverage> <side>\nExample: /open BTC 100 10 long',
        'close': 'Close a position: /close <position_id>\nExample: /close 123',
        'status': 'Get bot status: /status [detailed]\nExample: /status detailed',
        'balance': 'Check wallet balance: /balance [currency]\nExample: /balance USDC',
        'positions': 'List positions: /positions [status] [limit]\nExample: /positions open 5',
        'admin': 'Admin commands: /admin <action> [user_id]\nActions: status, users, emergency_stop, maintenance',
        'help': 'Get help: /help [command]\nExample: /help open',
    }
    
    return help_texts.get(command, f'No help available for {command}')
