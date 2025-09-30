import threading
import time


class InMemoryRedis:
    """Minimal in-memory Redis-like stub for tests.

    Provides get/set/expire/info and a simple lock context manager compatible
    with the usage in tests. Values are stored as bytes to emulate redis-py.
    """

    def __init__(self):
        self.store = {}
        self.expiry = {}
        self._locks = {}

    def ping(self):
        return True

    def _expired(self, key):
        ts = self.expiry.get(key)
        return ts is not None and time.time() >= ts

    def get(self, key):
        if self._expired(key):
            self.store.pop(key, None)
            self.expiry.pop(key, None)
            return None
        val = self.store.get(key)
        if val is None:
            return None
        return val if isinstance(val, (bytes, bytearray)) else str(val).encode()

    def set(self, key, value, ex=None):
        self.store[key] = (
            value if isinstance(value, (bytes, bytearray)) else str(value).encode()
        )
        if ex is not None:
            self.expiry[key] = time.time() + ex
        return True

    def expire(self, key, seconds):
        self.expiry[key] = time.time() + seconds
        return True

    def info(self, section="memory"):
        total = sum(
            len(v) for v in self.store.values() if isinstance(v, (bytes, bytearray))
        )
        return {"used_memory": total}

    def lock(self, key, timeout=5, blocking_timeout=5):
        if key not in self._locks:
            self._locks[key] = threading.Lock()
        lock = self._locks[key]

        class _Ctx:
            def __enter__(self_inner):
                acquired = lock.acquire(timeout=blocking_timeout)
                if not acquired:
                    raise TimeoutError("Could not acquire lock")
                return True

            def __exit__(self_inner, exc_type, exc, tb):
                lock.release()

        return _Ctx()
