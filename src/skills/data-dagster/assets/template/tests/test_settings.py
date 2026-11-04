"""Settings follow the py-code rules: environment only, secrets from NAME or
NAME_FILE, one error that names every bad variable and never a value."""

from pathlib import Path

import pytest

from dag.settings import Secret, Settings, SettingsError

ENV = {
    "SERVICE_NAME": "orders-dagster",
    "POSTGRES_HOST": "db",
    "POSTGRES_DB": "orders",
    "POSTGRES_USER": "reader",
    "POSTGRES_PASSWORD": "s3cret",
    "DAGSTER_PG_PASSWORD": "dagster-pw",
}


def test_loads_with_defaults():
    s = Settings(ENV)
    assert s.env_name == "local" and s.postgres_port == 5432
    assert "s3cret" in s.postgres_conninfo
    assert "s3cret" not in repr(s)


def test_missing_variables_are_named():
    with pytest.raises(SettingsError) as err:
        Settings({})
    text = str(err.value)
    assert "SERVICE_NAME" in text and "POSTGRES_PASSWORD" in text


def test_secret_from_file(tmp_path: Path):
    path = tmp_path / "pw"
    path.write_text("from-file\n")
    env = {k: v for k, v in ENV.items() if k != "POSTGRES_PASSWORD"}
    s = Settings({**env, "POSTGRES_PASSWORD_FILE": str(path)})
    assert s.postgres_password == Secret("from-file")


def test_env_example_loads_with_secrets_supplied():
    values = {}
    text = Path(__file__).parents[1].joinpath(".env.example").read_text()
    for line in text.splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            values[key] = value
    values["POSTGRES_PASSWORD"] = "x"
    values["DAGSTER_PG_PASSWORD"] = "y"
    Settings(values)
