"""Kafka settings: KAFKA_* from the environment."""

from __future__ import annotations

from dataclasses import dataclass

from ._base import EnvSettings, Secret, setting


@dataclass(init=False, repr=False, kw_only=True)
class KafkaSettings(EnvSettings):
    kafka_bootstrap_servers: str = setting("KAFKA_BOOTSTRAP_SERVERS")
    kafka_security_protocol: str = setting(
        "KAFKA_SECURITY_PROTOCOL", default="PLAINTEXT"
    )
    kafka_sasl_mechanism: str = setting(
        "KAFKA_SASL_MECHANISM", default="SCRAM-SHA-256"
    )
    kafka_sasl_username: str = setting("KAFKA_SASL_USERNAME", default="")
    # SECRET, required only for SASL_*: KAFKA_SASL_PASSWORD or ..._FILE
    kafka_sasl_password: Secret = setting(
        "KAFKA_SASL_PASSWORD", default=Secret("")
    )
    kafka_consumer_group: str = setting("KAFKA_CONSUMER_GROUP")

    def check(self) -> list[str]:
        sasl = self.kafka_security_protocol.upper().startswith("SASL_")
        password = self.kafka_sasl_password.get_secret_value()
        if sasl and not (self.kafka_sasl_username and password):
            return [
                "KAFKA_SASL_USERNAME and KAFKA_SASL_PASSWORD (or _FILE) "
                "are required when KAFKA_SECURITY_PROTOCOL is SASL_*"
            ]
        return []

    def kafka_client_config(self) -> dict[str, str]:
        """Settings every librdkafka client (producer, consumer) needs."""
        config = {
            "bootstrap.servers": self.kafka_bootstrap_servers,
            "security.protocol": self.kafka_security_protocol,
        }
        if self.kafka_security_protocol.upper().startswith("SASL_"):
            password = self.kafka_sasl_password.get_secret_value()
            config["sasl.mechanism"] = self.kafka_sasl_mechanism
            config["sasl.username"] = self.kafka_sasl_username
            config["sasl.password"] = password
        return config
