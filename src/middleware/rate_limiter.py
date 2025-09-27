import time
from collections import defaultdict

class RateLimiter:
    def __init__(self, max_requests=10, time_window=60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = defaultdict(list)
        
    def is_allowed(self, user_id: int) -> bool:
        now = time.time()
        user_requests = self.requests[user_id]
        
        # Clean old requests
        user_requests[:] = [req_time for req_time in user_requests 
                           if now - req_time < self.time_window]
        
        if len(user_requests) < self.max_requests:
            user_requests.append(now)
            return True
        
        return False

rate_limiter = RateLimiter()
