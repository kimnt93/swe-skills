"""Redis adapter (redis-py asyncio): client with timeouts, token-owned lock,
health.
"""

from __future__ import annotations

import secrets

from redis.asyncio import Redis

from ..settings import RedisSettings

# Compare-and-delete: release only if we still own the key (atomic in Lua).
_RELEASE = (
    "if redis.call('get', KEYS[1]) == ARGV[1] "
    "then return redis.call('del', KEYS[1]) else return 0 end"
)


class RedisClient:
    def __init__(self, settings: RedisSettings) -> None:
        self.r = Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password.get_secret_value(),
            socket_timeout=3,
            socket_connect_timeout=5,
            decode_responses=True,
        )

    async def ping(self) -> None:
        await self.r.ping()

    async def close(self) -> None:
        await self.r.aclose()

    async def lock(self, key: str, ttl_s: int):
        """Return an async release() on success, or None when someone else
        holds `key`.

        A lock is an optimisation guard; state transitions still need database
        locks and idempotency keys.
        """
        token = secrets.token_hex(16)
        if not await self.r.set(key, token, nx=True, ex=ttl_s):
            return None

        async def release() -> None:
            await self.r.eval(_RELEASE, 1, key, token)

        return release
