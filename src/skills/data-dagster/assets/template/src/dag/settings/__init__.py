"""Configuration: the only package that reads environment variables.

Same rules as every Python service in the stack (py-code): one class per
infrastructure, secrets are `Secret` read from `NAME` or `NAME_FILE` with no
default, a missing variable is listed by name and never by value.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from ._base import EnvSettings, Secret, SettingsError, setting
from .postgres import PostgresSettings


@dataclass(init=False, repr=False, kw_only=True)
class Settings(PostgresSettings, EnvSettings):
    # identity: the same names as the logging, tracing and errors skills
    service_name: str = setting("SERVICE_NAME")
    env_name: str = setting(
        "DEVELOPMENT_ENVIRONMENT", "ENV_NAME", "RUN_ENV", default="local"
    )
    node_name: str = setting("NODE_NAME", default="")
    service_version: str = setting("SERVICE_VERSION", default="")
    log_level: str = setting("LOG_LEVEL", default="info")
    # telemetry: empty endpoint turns metrics and traces off
    otel_endpoint: str = setting("OTEL_EXPORTER_OTLP_ENDPOINT", default="")
    otel_auth_token: Secret = setting("OTEL_AUTH_TOKEN", default=Secret(""))
    # error tracking: empty DSN turns it off
    sentry_dsn: Secret = setting("SENTRY_DSN", default=Secret(""))
    # Dagster's own storage and the output volume
    dagster_pg_host: str = setting("DAGSTER_PG_HOST", default="127.0.0.1")
    dagster_pg_db: str = setting("DAGSTER_PG_DB", default="dagster")
    dagster_pg_user: str = setting("DAGSTER_PG_USER", default="dagster")
    dagster_pg_password: Secret = setting("DAGSTER_PG_PASSWORD")
    output_dir: str = setting("OUTPUT_DIR", default="/var/lib/dagster-output")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # filled from the environment


__all__ = [
    "PostgresSettings",
    "Secret",
    "Settings",
    "SettingsError",
    "get_settings",
]
