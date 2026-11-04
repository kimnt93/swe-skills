"""Settings follow the py-code rules: environment only, secrets from NAME or
NAME_FILE, one error that names every bad variable and never a value."""

from pathlib import Path

import pytest

from pipeline.settings import Secret, Settings, SettingsError

ENV = {
    "SERVICE_NAME": "orders-pw-transform",
    "KAFKA_BOOTSTRAP_SERVERS": "127.0.0.1:9092",
    "KAFKA_CONSUMER_GROUP": "g",
    "KAFKA_TOPIC_IN": "in",
    "KAFKA_TOPIC_OUT": "out",
}


def test_loads_with_defaults():
    s = Settings(ENV)
    assert s.env_name == "local" and s.window_seconds == 60
    assert s.pathway_kafka()["group.id"] == "g"
    assert s.sentry_dsn == Secret("")


def test_missing_variables_are_named():
    with pytest.raises(SettingsError) as err:
        Settings({})
    text = str(err.value)
    assert "SERVICE_NAME" in text and "KAFKA_TOPIC_IN" in text


def test_secret_from_file_and_never_in_repr(tmp_path: Path):
    path = tmp_path / "dsn"
    path.write_text("https://key@sentry.example/1\n")
    s = Settings({**ENV, "SENTRY_DSN_FILE": str(path)})
    assert s.sentry_dsn.get_secret_value() == "https://key@sentry.example/1"
    assert "key@" not in repr(s)


def test_sasl_needs_credentials():
    env = {**ENV, "KAFKA_SECURITY_PROTOCOL": "SASL_SSL"}
    with pytest.raises(SettingsError):
        Settings(env)


def test_env_example_loads_with_secrets_blank():
    values = {}
    text = Path(__file__).parents[1].joinpath(".env.example").read_text()
    for line in text.splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            values[key] = value
    Settings(values)
