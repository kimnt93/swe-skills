from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import pytest

from service.settings import KafkaSettings, Settings, SettingsError

SECRETS = [
    "POSTGRES_PASSWORD",
    "REDIS_PASSWORD",
    "S3_ACCESS_KEY",
    "S3_SECRET_KEY",
    "INTERNAL_SERVICE_TOKEN",
]


def test_loads_with_defaults(env):
    for name in (
        "POSTGRES_PORT",
        "POSTGRES_SSLMODE",
        "REDIS_PORT",
        "HTTP_PORT",
        "S3_REGION",
    ):
        env.delenv(name, raising=False)  # the shell may set them
    s = Settings()
    assert s.postgres_port == 5432
    assert s.http_port == 3000
    assert s.postgres_sslmode == "require"
    assert s.s3_force_path_style is True
    assert s.s3_region == "us-east-1"


@pytest.mark.parametrize("name", SECRETS)
def test_every_secret_is_required_by_name(env, name):
    env.delenv(name)
    with pytest.raises(SettingsError) as err:
        Settings()
    assert name in str(err.value)


def test_secret_from_file_and_never_in_repr(env, tmp_path):
    f = tmp_path / "pw"
    f.write_text("s3cret\n")
    env.delenv("POSTGRES_PASSWORD")
    env.setenv("POSTGRES_PASSWORD_FILE", str(f))
    s = Settings()
    assert s.postgres_password.get_secret_value() == "s3cret"
    assert "s3cret" not in repr(s)
    assert "s3cret" not in str(asdict(s))


def test_kafka_sasl_needs_credentials(env):
    env.setenv("KAFKA_SECURITY_PROTOCOL", "SASL_SSL")
    with pytest.raises(SettingsError) as err:
        KafkaSettings()
    assert "KAFKA_SASL_USERNAME" in str(err.value)
    env.setenv("KAFKA_SASL_USERNAME", "u")
    env.setenv("KAFKA_SASL_PASSWORD", "p")
    config = KafkaSettings().kafka_client_config()
    assert config["sasl.username"] == "u"
    assert config["security.protocol"] == "SASL_SSL"


def test_plaintext_kafka_config_has_no_sasl_keys(env):
    assert "sasl.username" not in KafkaSettings().kafka_client_config()


def test_env_example_is_complete(monkeypatch):
    """Every variable the settings read is documented and nothing else is
    required; secrets are blank in the example (no defaults)."""
    example = Path(__file__).parents[1] / ".env.example"
    for line in example.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        if key.endswith(("PASSWORD", "TOKEN", "KEY")):
            assert value == "", f"{key} must be blank: secrets have no default"
            value = "dummy-secret"
        monkeypatch.setenv(key, value)
    Settings()
