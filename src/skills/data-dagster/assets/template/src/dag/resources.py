"""Resources: how assets reach the outside world. Assets take the abstract
`OrdersSource`; tests pass a fake, production passes `PostgresOrders`."""

from __future__ import annotations

from datetime import date

from dagster import ConfigurableResource

ORDERS_SQL = """
SELECT order_id, symbol, price, qty, created_at
FROM orders
WHERE created_at >= %(start)s
  AND created_at < %(start)s + interval '1 day'
ORDER BY created_at
"""


class OrdersSource(ConfigurableResource):
    def fetch(self, day: date) -> list[dict]:
        raise NotImplementedError


class PostgresOrders(OrdersSource):
    """Built from `PostgresSettings.postgres_conninfo`; the conninfo holds
    the password, so it is never logged."""

    conninfo: str

    def fetch(self, day: date) -> list[dict]:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(
            self.conninfo, row_factory=dict_row
        ) as connection:
            return connection.execute(ORDERS_SQL, {"start": day}).fetchall()
