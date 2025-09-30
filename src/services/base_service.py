"""Base service helpers shared by async service implementations."""

from abc import ABC, abstractmethod
from typing import Any, Optional

from src.utils.logging import get_logger

logger = get_logger(__name__)


class BaseService(ABC):
    """Base service class with common logging functionality."""

    def __init__(self) -> None:
        self.logger = logger

    @abstractmethod
    def validate_input(self, data: dict[str, Any]) -> bool:
        """Validate input data for the service."""
        raise NotImplementedError

    def log_operation(
        self, operation: str, user_id: Optional[int] = None, **kwargs: Any
    ) -> None:
        """Log service operation with structured metadata."""
        log_data = {
            "operation": operation,
            "service": self.__class__.__name__,
            "user_id": user_id,
            **kwargs,
        }
        self.logger.info("Service operation", extra={"service_operation": log_data})
