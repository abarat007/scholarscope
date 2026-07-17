"""Key-value cache with a Redis implementation and an in-memory test double.

Extraction results are immutable per (paper, schema version), so they are
cached without TTL.
"""

from typing import Protocol

import redis.asyncio as aioredis

from src.config import get_settings


class KVCache(Protocol):
    async def get(self, key: str) -> str | None: ...
    async def set(self, key: str, value: str) -> None: ...


class RedisCache:
    def __init__(self, url: str | None = None):
        self._redis = aioredis.from_url(url or get_settings().redis_url, decode_responses=True)

    async def get(self, key: str) -> str | None:
        return await self._redis.get(key)

    async def set(self, key: str, value: str) -> None:
        await self._redis.set(key, value)


class InMemoryCache:
    def __init__(self):
        self.data: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.data.get(key)

    async def set(self, key: str, value: str) -> None:
        self.data[key] = value


_cache: KVCache | None = None


def get_cache() -> KVCache:
    global _cache
    if _cache is None:
        _cache = RedisCache()
    return _cache
