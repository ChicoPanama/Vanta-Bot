from __future__ import annotations
import time
from typing import Dict, Tuple

class SimpleRateLimiter:
    def __init__(self, per_user_limit: Tuple[int,int] = (5, 10)):
        # (N calls, per seconds)
        self.N, self.window = per_user_limit
        self.bucket: Dict[int, list] = {}

    def allow(self, uid: int) -> bool:
        now = time.time()
        q = self.bucket.get(uid, [])
        q = [t for t in q if now - t < self.window]
        if len(q) >= self.N:
            self.bucket[uid] = q
            return False
        q.append(now)
        self.bucket[uid] = q
        return True

# single global limiter for heavy routes (quotes/positions)
quote_limiter = SimpleRateLimiter((8, 10))     # 8 calls / 10s
pos_limiter   = SimpleRateLimiter((5, 10))     # 5 calls / 10s
