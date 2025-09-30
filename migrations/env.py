# migrations/env.py
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Import your models
from src.database.models import Base

# this is the Alembic Config object
config_alembic = context.config

# Interpret the config file for Python logging
if config_alembic.config_file_name is not None:
    fileConfig(config_alembic.config_file_name)

# Target metadata for autogenerate
target_metadata = Base.metadata


def _sync_url():
    """Get sync database URL for Alembic (no async drivers)."""
    url = context.get_x_argument(as_dictionary=True).get("url")
    if not url:
        # Fallback to env or default file
        url = os.getenv("DATABASE_URL", "sqlite:///vanta_bot.db")
    # Force sync if someone passes aiosqlite
    if "sqlite+aiosqlite://" in url:
        url = url.replace("sqlite+aiosqlite://", "sqlite:///")
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = _sync_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode with sync engine."""
    connectable = create_engine(
        _sync_url() + "?timeout=30",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
