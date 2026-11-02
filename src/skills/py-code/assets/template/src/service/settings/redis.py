"""Redis settings: REDIS_* from the environment."""

from __future__ import annotations

from dataclasses import dataclass

from ._base import EnvSettings, Secret, setting


@dataclass(init=False, repr=False, kw_only=True)
class RedisSettings(EnvSettings):
    redis_host: str = setting("REDIS_HOST")
    redis_port: int = setting("REDIS_PORT", default=6379)
    redis_db: int = setting("REDIS_DB", default=0, ge=0)
    # SECRET: required, no default; REDIS_PASSWORD or ..._FILE
    redis_password: Secret = setting("REDIS_PASSWORD")
