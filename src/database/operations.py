"""Database operations backed by SQLAlchemy AsyncSession helpers."""

from __future__ import annotations

import logging
import os
from collections.abc import Awaitable
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

try:
    from src.config.settings import settings
except Exception:  # pragma: no cover - allows usage before settings wiring
    settings = None

from src.database import models

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Thin wrapper around SQLAlchemy async engine providing helpers."""

    def __init__(self, database_url: str | None = None) -> None:
        env_value = os.getenv("DATABASE_URL")
        fallback = "sqlite+aiosqlite:///vanta_bot.db"

        if database_url:
            url = database_url
        elif env_value:
            url = env_value
        elif settings is not None and getattr(settings, "DATABASE_URL", None):
            url = settings.DATABASE_URL
        else:
            url = fallback

        if url.startswith("sqlite:///") and "+aiosqlite" not in url:
            url = url.replace("sqlite:///", "sqlite+aiosqlite:///")

        logger.debug(
            "DatabaseManager initialised with %s backend", url.split(":", 1)[0]
        )

        self.engine = create_async_engine(url, pool_pre_ping=True, future=True)
        self.session_factory = async_sessionmaker(
            bind=self.engine, expire_on_commit=False
        )

    async def _run(
        self,
        operation: Callable[[AsyncSession], Awaitable[Any]],
        *,
        commit: bool = False,
    ) -> Any:
        async with self.session_factory() as session:
            try:
                result = await operation(session)
                if commit:
                    await session.commit()
                return result
            except Exception:  # noqa: BLE001
                if commit:
                    await session.rollback()
                raise

    # ------------------------------------------------------------------
    # Schema management

    async def create_tables(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)

    # ------------------------------------------------------------------
    # Users

    async def get_user(self, telegram_id: int) -> models.User | None:
        async def op(session: AsyncSession) -> models.User | None:
            result = await session.execute(
                select(models.User).where(models.User.telegram_id == telegram_id)
            )
            return result.scalars().first()

        return await self._run(op)

    async def get_user_by_id(self, user_id: int) -> models.User | None:
        async def op(session: AsyncSession) -> models.User | None:
            result = await session.execute(
                select(models.User).where(models.User.id == user_id)
            )
            return result.scalars().first()

        return await self._run(op)

    async def create_user(
        self,
        *,
        telegram_id: int,
        username: str | None,
        wallet_address: str,
        encrypted_private_key: str,
    ) -> models.User:
        async def op(session: AsyncSession) -> models.User:
            user = models.User(
                telegram_id=telegram_id,
                username=username,
                wallet_address=wallet_address,
                encrypted_private_key=encrypted_private_key,
            )
            session.add(user)
            await session.flush()
            await session.refresh(user)
            return user

        return await self._run(op, commit=True)

    # ------------------------------------------------------------------
    # Positions

    async def create_position(
        self,
        *,
        user_id: int,
        symbol: str,
        side: str,
        size: float,
        leverage: int,
        entry_price: float | None = None,
    ) -> models.Position:
        async def op(session: AsyncSession) -> models.Position:
            position = models.Position(
                user_id=user_id,
                symbol=symbol,
                side=side,
                size=size,
                leverage=leverage,
                entry_price=entry_price,
            )
            session.add(position)
            await session.flush()
            await session.refresh(position)
            return position

        return await self._run(op, commit=True)

    async def get_user_positions(
        self, user_id: int, status: str | None = None
    ) -> list[models.Position]:
        async def op(session: AsyncSession) -> list[models.Position]:
            stmt = select(models.Position).where(models.Position.user_id == user_id)
            if status:
                stmt = stmt.where(models.Position.status == status)
            result = await session.execute(
                stmt.order_by(models.Position.opened_at.desc())
            )
            return list(result.scalars().all())

        return await self._run(op)

    async def get_position_by_id(self, position_id: int) -> models.Position | None:
        async def op(session: AsyncSession) -> models.Position | None:
            result = await session.execute(
                select(models.Position).where(models.Position.id == position_id)
            )
            return result.scalars().first()

        return await self._run(op)

    async def update_position(
        self, position_id: int, **kwargs: Any
    ) -> models.Position | None:
        async def op(session: AsyncSession) -> models.Position | None:
            position = await session.get(models.Position, position_id)
            if not position:
                return None
            for key, value in kwargs.items():
                setattr(position, key, value)
            await session.flush()
            await session.refresh(position)
            return position

        return await self._run(op, commit=True)

    async def list_recent_closed_positions(
        self, user_id: int, limit: int = 10
    ) -> list[models.Position]:
        async def op(session: AsyncSession) -> list[models.Position]:
            stmt = (
                select(models.Position)
                .where(
                    models.Position.user_id == user_id,
                    models.Position.status == "CLOSED",
                )
                .order_by(models.Position.closed_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

        return await self._run(op)

    async def list_open_positions(self) -> list[models.Position]:
        async def op(session: AsyncSession) -> list[models.Position]:
            result = await session.execute(
                select(models.Position).where(models.Position.status == "OPEN")
            )
            return list(result.scalars().all())

        return await self._run(op)

    # ------------------------------------------------------------------
    # Orders

    async def list_pending_orders(self, user_id: int) -> list[models.Order]:
        async def op(session: AsyncSession) -> list[models.Order]:
            result = await session.execute(
                select(models.Order).where(
                    models.Order.user_id == user_id,
                    models.Order.status == "PENDING",
                )
            )
            return list(result.scalars().all())

        return await self._run(op)

    async def create_order(
        self,
        *,
        user_id: int,
        symbol: str,
        order_type: str,
        side: str,
        size: float,
        leverage: int,
        price: float | None = None,
    ) -> models.Order:
        async def op(session: AsyncSession) -> models.Order:
            order = models.Order(
                user_id=user_id,
                symbol=symbol,
                order_type=order_type,
                side=side,
                size=size,
                leverage=leverage,
                price=price,
            )
            session.add(order)
            await session.flush()
            await session.refresh(order)
            return order

        return await self._run(op, commit=True)

    # ------------------------------------------------------------------
    # Transactions

    async def create_transaction(
        self,
        *,
        user_id: int,
        tx_hash: str,
        tx_type: str,
        amount: float | None = None,
        status: str = "PENDING",
    ) -> models.Transaction:
        async def op(session: AsyncSession) -> models.Transaction:
            tx = models.Transaction(
                user_id=user_id,
                tx_hash=tx_hash,
                tx_type=tx_type,
                amount=amount,
                status=status,
            )
            session.add(tx)
            await session.flush()
            await session.refresh(tx)
            return tx

        return await self._run(op, commit=True)

    async def run_in_session(
        self,
        operation: Callable[[AsyncSession], Awaitable[Any]],
        *,
        commit: bool = False,
    ) -> Any:
        """Execute a custom operation with an async session."""
        return await self._run(operation, commit=commit)


db = DatabaseManager()
