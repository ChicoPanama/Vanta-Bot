import os
import sys
from pathlib import Path

# Ensure local sqlite database is used during tests without requiring settings singleton
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///vanta_bot.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("BASE_RPC_URL", "memory")
os.environ.setdefault("ENCRYPTION_KEY", "u6C6J16mPzJ9ZhDJW60Trw7P3cu6UytzszbmWzxubEU=")
os.environ.setdefault("AVANTIS_TRADING_CONTRACT", "0x0000000000000000000000000000000000000000")
# Avoid leaking host DEBUG into tests expecting defaults
os.environ.pop("DEBUG", None)

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def pytest_configure(config):
    config.addinivalue_line("markers", "asyncio: mark test as asynchronous")
