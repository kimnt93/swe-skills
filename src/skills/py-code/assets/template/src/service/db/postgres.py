"""PostgreSQL adapter: psycopg 3 + connection pool, plain parameterised SQL, no
ORM.

SQL lives only here. Rows are mapped to domain types at the edge. Schema
changes are goose files in schemas/.
"""

from __future__ import annotations

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from ..application.ports import ItemRepository
from ..domain.item import Item, NotFoundError
from ..settings import PostgresSettings

# One query per constant, written the way psql would run it: one clause per
# line, one column per line. No casts in the select list: rows are converted
# in _to_item.
INSERT_ITEM_SQL = """
INSERT INTO items (id, name, created_at)
VALUES (%s, %s, %s)
"""

GET_ITEM_SQL = """
SELECT
    id,
    name,
    created_at
FROM items
WHERE id = %s
"""

LIST_ITEMS_SQL = """
SELECT
    id,
    name,
    created_at
FROM items
WHERE id = ANY(%s::uuid[])
ORDER BY created_at DESC
LIMIT 500
"""

UPSERT_ITEM_SQL = """
INSERT INTO items (id, name, created_at)
VALUES (%s, %s, %s)
ON CONFLICT (id) DO UPDATE
SET name = EXCLUDED.name
"""

CLAIM_ITEM_SQL = """
SELECT
    id,
    name,
    created_at
FROM items
ORDER BY created_at
LIMIT 1
FOR UPDATE SKIP LOCKED
"""


def _to_item(row: dict) -> Item:
    return Item(
        id=str(row["id"]),
        name=row["name"],
        created_at=row["created_at"],
    )


class PostgresItems:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self.pool = pool

    @classmethod
    async def open(
        cls, settings: PostgresSettings, *, max_size: int = 10
    ) -> PostgresItems:
        pool = AsyncConnectionPool(
            settings.postgres_conninfo,
            min_size=1,
            max_size=max_size,
            open=False,
            kwargs={"row_factory": dict_row, "connect_timeout": 5},
        )
        await pool.open(wait=True, timeout=10)
        return cls(pool)

    async def close(self) -> None:
        await self.pool.close()

    async def ping(self) -> None:
        async with self.pool.connection() as conn:
            await conn.execute("SELECT 1")

    async def create(self, item: Item) -> None:
        # One transaction per operation: the connection context commits on
        # success, rolls back on error.
        async with self.pool.connection() as conn:
            await conn.execute(
                INSERT_ITEM_SQL,
                (item.id, item.name, item.created_at),
            )

    async def get(self, id: str) -> Item:
        async with self.pool.connection() as conn:
            cur = await conn.execute(GET_ITEM_SQL, (id,))
            row = await cur.fetchone()

        if row is None:
            raise NotFoundError(f"item {id}")

        return _to_item(row)

    async def list_by_ids(self, ids: list[str]) -> list[Item]:
        """One query for a set (no N+1), bounded."""
        if not ids:
            return []

        async with self.pool.connection() as conn:
            cur = await conn.execute(LIST_ITEMS_SQL, (ids,))
            rows = await cur.fetchall()

        return [_to_item(row) for row in rows]

    async def upsert(self, item: Item) -> None:
        """Idempotent write: a replayed message converges on one row."""
        async with self.pool.connection() as conn:
            await conn.execute(
                UPSERT_ITEM_SQL,
                (item.id, item.name, item.created_at),
            )

    async def claim_oldest(self) -> Item | None:
        """Claim one row with FOR UPDATE SKIP LOCKED so replicas never block
        each other; commit ends the claim.
        """
        async with self.pool.connection() as conn, conn.transaction():
            cur = await conn.execute(CLAIM_ITEM_SQL)
            row = await cur.fetchone()

            if row is None:
                return None

            return _to_item(row)


_: ItemRepository = PostgresItems.__new__(
    PostgresItems
)  # structural check that the adapter fits the port
