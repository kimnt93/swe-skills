"""PostgreSQL settings: POSTGRES_* from the environment."""

from __future__ import annotations

from dataclasses import dataclass

from ._base import EnvSettings, Secret, setting


@dataclass(init=False, repr=False, kw_only=True)
class PostgresSettings(EnvSettings):
    postgres_host: str = setting("POSTGRES_HOST")
    postgres_port: int = setting("POSTGRES_PORT", default=5432)
    postgres_db: str = setting("POSTGRES_DB")
    postgres_user: str = setting("POSTGRES_USER")
    # SECRET: required, no default; POSTGRES_PASSWORD or ..._FILE
    postgres_password: Secret = setting("POSTGRES_PASSWORD")
    postgres_sslmode: str = setting("POSTGRES_SSLMODE", default="require")
    postgres_pool_size: int = setting("POSTGRES_POOL_SIZE", default=10, ge=1)

    @property
    def postgres_conninfo(self) -> str:
        """libpq conninfo; contains the password, so never log it."""
        return (
            f"host={self.postgres_host} port={self.postgres_port} "
            f"dbname={self.postgres_db} user={self.postgres_user} "
            f"password={self.postgres_password.get_secret_value()} "
            f"sslmode={self.postgres_sslmode}"
        )
