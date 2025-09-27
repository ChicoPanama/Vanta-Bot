"""
Base Service
Abstract base class for all services with common functionality
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from src.database.operations import db
from src.utils.logging import get_logger

logger = get_logger(__name__)


class BaseService(ABC):
    """Base service class with common database and logging functionality"""
    
    def __init__(self):
        self.logger = logger
    
    @property
    def session(self) -> Session:
        """Get database session"""
        return db.get_session()
    
    def execute_with_session(self, operation: callable, *args, **kwargs) -> Any:
        """Execute operation with proper session management"""
        session = self.session
        try:
            result = operation(session, *args, **kwargs)
            session.commit()
            return result
        except Exception as e:
            session.rollback()
            self.logger.error(f"Database operation failed: {e}")
            raise
        finally:
            session.close()
    
    @abstractmethod
    def validate_input(self, data: Dict[str, Any]) -> bool:
        """Validate input data for the service"""
        pass
    
    def log_operation(self, operation: str, user_id: Optional[int] = None, **kwargs):
        """Log service operation"""
        log_data = {
            "operation": operation,
            "service": self.__class__.__name__,
            "user_id": user_id,
            **kwargs
        }
        self.logger.info(f"Service operation: {log_data}")
