"""Database session management with proper lifecycle."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Callable

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config.settings import settings

logger = logging.getLogger(__name__)


class DatabaseSessionManager:
    """Manages database sessions with proper lifecycle."""

    def __init__(self, database_url: str = None):
        """Initialize with database URL."""
        self.database_url = database_url or settings.DATABASE_URL
        self.engine: AsyncEngine = None
        self.session_factory: Callable[[], AsyncSession] = None
        self._initialized = False

    def initialize(self):
        """Initialize database engine and session factory."""
        if self._initialized:
            return

        try:
            self.engine = create_async_engine(
                self.database_url,
                pool_pre_ping=True,
                future=True,
                echo=False,  # Set to True for SQL debugging
            )
            self.session_factory = async_sessionmaker(
                bind=self.engine, expire_on_commit=False, class_=AsyncSession
            )
            self._initialized = True
            logger.info("Database session manager initialized")

        except Exception as e:
            logger.error(f"Failed to initialize database session manager: {e}")
            raise

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session with proper cleanup.

        Yields:
            AsyncSession: Database session
        """
        if not self._initialized:
            self.initialize()

        session = self.session_factory()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def close(self):
        """Close database engine."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database engine disposed")


# Global session manager
_session_manager: DatabaseSessionManager = None


def get_session_manager() -> DatabaseSessionManager:
    """Get global session manager."""
    global _session_manager
    if _session_manager is None:
        _session_manager = DatabaseSessionManager()
    return _session_manager


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session from global manager."""
    manager = get_session_manager()
    async for session in manager.get_session():
        yield session
