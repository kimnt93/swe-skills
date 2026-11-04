"""Settings from the environment. Secrets come from NAME or NAME_FILE and
have no default; a missing required variable is listed by name, never by
value."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class ConfigError(Exception):
    pass


def _read(name: str, required: bool = True, default: str = "") -> str:
    path = os.environ.get(f"{name}_FILE")
    if path:
        return Path(path).read_text(encoding="utf-8").strip()
    value = os.environ.get(name, default)
    if required and not value:
        raise ConfigError(f"{name} is required")
    return value


@dataclass(frozen=True)
class Settings:
    service_name: str
    env_name: str
    bootstrap: str
    group_id: str
    topic_in: str
    topic_out: str
    username: str
    password: str
    window_seconds: int
    persistence_dir: str
    otlp_endpoint: str
    otlp_token: str

    def kafka(self) -> dict:
        """rdkafka settings for pw.io.kafka.read / write."""
        settings = {
            "bootstrap.servers": self.bootstrap,
            "group.id": self.group_id,
            "auto.offset.reset": "earliest",
        }
        if self.username:
            settings.update(
                {
                    "security.protocol": "sasl_ssl",
                    "sasl.mechanism": "SCRAM-SHA-512",
                    "sasl.username": self.username,
                    "sasl.password": self.password,
                }
            )
        return settings


def load() -> Settings:
    return Settings(
        service_name=_read("SERVICE_NAME"),
        env_name=_read("ENV_NAME", default="local"),
        bootstrap=_read("KAFKA_BOOTSTRAP_SERVERS"),
        group_id=_read("KAFKA_GROUP_ID"),
        topic_in=_read("KAFKA_TOPIC_IN"),
        topic_out=_read("KAFKA_TOPIC_OUT"),
        username=_read("KAFKA_USERNAME", required=False),
        password=_read("KAFKA_PASSWORD", required=False),
        window_seconds=int(_read("WINDOW_SECONDS", default="60")),
        persistence_dir=_read("PERSISTENCE_DIR", default=""),
        otlp_endpoint=_read("OTEL_EXPORTER_OTLP_ENDPOINT", required=False),
        otlp_token=_read("OTEL_EXPORTER_OTLP_TOKEN", required=False),
    )
