"""Configuration: the only package that reads environment variables.

Same rules as every Python service in the stack (py-code): one class per
infrastructure, secrets are `Secret` read from `NAME` or `NAME_FILE` with no
default, a missing variable is listed by name and never by value.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from ._base import EnvSettings, Secret, SettingsError, setting
from .kafka import KafkaSettings


@dataclass(init=False, repr=False, kw_only=True)
class Settings(KafkaSettings, EnvSettings):
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
    # the job
    kafka_topic_in: str = setting("KAFKA_TOPIC_IN")
    kafka_topic_out: str = setting("KAFKA_TOPIC_OUT")
    window_seconds: int = setting("WINDOW_SECONDS", default=60, ge=1)
    persistence_dir: str = setting("PERSISTENCE_DIR", default="")

    def pathway_kafka(self) -> dict[str, str]:
        """rdkafka settings for pw.io.kafka.read / write."""
        config = self.kafka_client_config()
        config["group.id"] = self.kafka_consumer_group
        config["auto.offset.reset"] = "earliest"
        return config


@lru_cache
def get_settings() -> Settings:
    return Settings()  # filled from the environment


__all__ = [
    "KafkaSettings",
    "Secret",
    "Settings",
    "SettingsError",
    "get_settings",
]
