import redis
import json
from src.config.settings import config

class CacheService:
    def __init__(self):
        self.redis_client = redis.from_url(config.REDIS_URL)
        
    def set(self, key: str, value: dict, ttl: int = 300):
        """Set cache value with TTL"""
        self.redis_client.setex(key, ttl, json.dumps(value))
        
    def get(self, key: str):
        """Get cache value"""
        cached = self.redis_client.get(key)
        return json.loads(cached) if cached else None
        
    def delete(self, key: str):
        """Delete cache key"""
        self.redis_client.delete(key)

cache = CacheService()
