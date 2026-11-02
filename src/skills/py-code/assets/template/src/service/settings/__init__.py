"""Configuration: the only package that reads environment variables.

`Settings` composes the per-infrastructure classes. A service that does not
use one deletes its module and its base class here. Names follow the
deployment contract (POSTGRES_*, REDIS_*, KAFKA_*, S3_*); secrets are
`Secret`, read from `NAME` or `NAME_FILE`, and never have a default.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from ._base import EnvSettings, Secret, SettingsError, setting
from .kafka import KafkaSettings
from .postgres import PostgresSettings
from .redis import RedisSettings
from .s3 import S3Settings


@dataclass(init=False, repr=False, kw_only=True)
class Settings(
    PostgresSettings, RedisSettings, KafkaSettings, S3Settings, EnvSettings
):
    # required: no default identity
    service_name: str = setting("SERVICE_NAME")
    # env name: DEVELOPMENT_ENVIRONMENT, else ENV_NAME, else RUN_ENV (the
    # same order as the log format); it is also the middle label of the host.
    env_name: str = setting(
        "DEVELOPMENT_ENVIRONMENT", "ENV_NAME", "RUN_ENV", default="local"
    )
    node_name: str = setting("NODE_NAME", default="")
    service_version: str = setting("SERVICE_VERSION", default="")
    log_level: str = setting("LOG_LEVEL", default="info")
    http_host: str = setting("HTTP_HOST", default="0.0.0.0")
    http_port: int = setting("HTTP_PORT", default=3000, ge=1, le=65535)
    internal_service_token: Secret = setting("INTERNAL_SERVICE_TOKEN")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # filled from the environment


__all__ = [
    "KafkaSettings",
    "PostgresSettings",
    "RedisSettings",
    "S3Settings",
    "Secret",
    "Settings",
    "SettingsError",
    "get_settings",
]
