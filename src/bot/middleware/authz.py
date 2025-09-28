"""Authorization middleware for bot commands."""

import logging
from typing import List, Optional
from src.config.settings import settings

logger = logging.getLogger(__name__)


class AuthorizationMiddleware:
    """Authorization middleware for bot commands."""
    
    def __init__(self):
        self.admin_user_ids = set(settings.ADMIN_USER_IDS)
        self.super_admin_ids = set(settings.SUPER_ADMIN_IDS)
        
        # Command permissions
        self.command_permissions = {
            'start': 'all',  # All users
            'help': 'all',
            'status': 'all',
            'open': 'all',
            'close': 'all',
            'positions': 'all',
            'balance': 'all',
            'admin': 'admin',  # Admin only
            'emergency_stop': 'super_admin',  # Super admin only
            'maintenance': 'admin',
            'users': 'admin',
            'metrics': 'admin',
        }

    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if admin
        """
        return user_id in self.admin_user_ids

    def is_super_admin(self, user_id: int) -> bool:
        """Check if user is super admin.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if super admin
        """
        return user_id in self.super_admin_ids

    def can_execute_command(self, user_id: int, command: str) -> bool:
        """Check if user can execute command.
        
        Args:
            user_id: User identifier
            command: Command name
            
        Returns:
            True if allowed
        """
        try:
            # Get required permission level
            required_permission = self.command_permissions.get(command, 'all')
            
            if required_permission == 'all':
                return True
            elif required_permission == 'admin':
                return self.is_admin(user_id)
            elif required_permission == 'super_admin':
                return self.is_super_admin(user_id)
            else:
                logger.warning(f"Unknown permission level: {required_permission}")
                return False
                
        except Exception as e:
            logger.error(f"Authorization check failed for user {user_id}, command {command}: {e}")
            return False

    def get_user_permissions(self, user_id: int) -> List[str]:
        """Get user permission levels.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of permission levels
        """
        permissions = ['user']  # All users have basic permissions
        
        if self.is_admin(user_id):
            permissions.append('admin')
        
        if self.is_super_admin(user_id):
            permissions.append('super_admin')
        
        return permissions

    def get_available_commands(self, user_id: int) -> List[str]:
        """Get commands available to user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of available commands
        """
        available_commands = []
        
        for command, required_permission in self.command_permissions.items():
            if self.can_execute_command(user_id, command):
                available_commands.append(command)
        
        return available_commands

    def add_admin(self, user_id: int) -> bool:
        """Add user to admin list.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if added successfully
        """
        try:
            if user_id not in self.admin_user_ids:
                self.admin_user_ids.add(user_id)
                logger.info(f"Added user {user_id} to admin list")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to add admin {user_id}: {e}")
            return False

    def remove_admin(self, user_id: int) -> bool:
        """Remove user from admin list.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if removed successfully
        """
        try:
            if user_id in self.admin_user_ids:
                self.admin_user_ids.remove(user_id)
                logger.info(f"Removed user {user_id} from admin list")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to remove admin {user_id}: {e}")
            return False

    def add_super_admin(self, user_id: int) -> bool:
        """Add user to super admin list.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if added successfully
        """
        try:
            if user_id not in self.super_admin_ids:
                self.super_admin_ids.add(user_id)
                logger.info(f"Added user {user_id} to super admin list")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to add super admin {user_id}: {e}")
            return False

    def remove_super_admin(self, user_id: int) -> bool:
        """Remove user from super admin list.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if removed successfully
        """
        try:
            if user_id in self.super_admin_ids:
                self.super_admin_ids.remove(user_id)
                logger.info(f"Removed user {user_id} from super admin list")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to remove super admin {user_id}: {e}")
            return False


# Global authorization middleware
authz_middleware = AuthorizationMiddleware()
