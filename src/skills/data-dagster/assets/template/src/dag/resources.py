"""Resources: how assets reach the outside world. Assets take the abstract
`OrdersSource`; tests pass a fake, production passes `PostgresOrders`."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from dagster import ConfigurableResource

ORDERS_SQL = """
SELECT order_id, symbol, price, qty, created_at
FROM orders
WHERE created_at >= %(start)s
  AND created_at < %(start)s + interval '1 day'
ORDER BY created_at
"""


def secret(name: str) -> str:
    """NAME_FILE (a Swarm secret) wins over NAME; no default."""
    path = os.environ.get(f"{name}_FILE")
    if path:
        return Path(path).read_text(encoding="utf-8").strip()
    return os.environ.get(name, "")


class OrdersSource(ConfigurableResource):
    def fetch(self, day: date) -> list[dict]:
        raise NotImplementedError


class PostgresOrders(OrdersSource):
    host: str
    port: int
    database: str
    user: str

    def fetch(self, day: date) -> list[dict]:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(
            host=self.host,
            port=self.port,
            dbname=self.database,
            user=self.user,
            password=secret("POSTGRES_PASSWORD"),
            row_factory=dict_row,
        ) as connection:
            return connection.execute(ORDERS_SQL, {"start": day}).fetchall()
