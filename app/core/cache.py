import json
from typing import Any, Optional

from redis.asyncio import ConnectionPool, Redis

from app.core.config import settings

# Create connection pool
pool = ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True, max_connections=50)


async def get_redis() -> Redis:
    """Get Redis client"""
    return Redis(connection_pool=pool)


class CacheService:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        value = await self.redis.get(key)
        if value:
            return json.loads(value)
        return None

    async def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """Set value in cache with expiration"""
        return await self.redis.setex(key, expire, json.dumps(value))

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        return await self.redis.delete(key) > 0

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        return await self.redis.exists(key) > 0

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter"""
        return await self.redis.incrby(key, amount)

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on key"""
        return await self.redis.expire(key, seconds)
