"""Optional SQLAlchemy 2 adapter (async).

Use it when the project asks for an ORM or already has one; the default
adapter is raw SQL (py-code/references/postgres.md). Both implement the same
port, so one replaces the other. SQLAlchemy speaks PostgreSQL, MySQL, SQLite,
SQL Server and Oracle: the only database-specific part is the async URL passed
to Store.open (postgresql+asyncpg://, mysql+aiomysql://, sqlite+aiosqlite://).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import DateTime, String, Uuid, select, text, update
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class NotFound(Exception):
    """The row does not exist."""


@dataclass(frozen=True, slots=True)
class Item:
    """The domain view of a row. ORM objects never leave the adapter."""

    id: str
    name: str
    created_at: datetime


class Base(DeclarativeBase):
    pass


class ItemRow(Base):
    """Maps the items table.

    Every column is NOT NULL, so no attribute is Optional. Uuid(as_uuid=False)
    is a native uuid on PostgreSQL and a CHAR on databases without one; the
    domain id stays a str.
    """

    __tablename__ = "items"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    name: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Store:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine
        self._sessions = async_sessionmaker(engine, expire_on_commit=False)

    @classmethod
    def open(cls, url: str, pool_size: int = 5) -> Store:
        """url is an async SQLAlchemy URL.

        Build it from the same POSTGRES_* settings as the raw adapter with
        URL.create, so the password is never formatted into a string you
        might log.
        """
        kwargs = {} if url.startswith("sqlite") else {"pool_size": pool_size}
        return cls(create_async_engine(url, **kwargs))

    async def close(self) -> None:
        await self._engine.dispose()

    async def ping(self) -> None:
        """The database check of /healthz."""
        async with self._engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

    async def create(self, item: Item) -> None:
        async with self._sessions() as session, session.begin():
            session.add(_row(item))

    async def get(self, item_id: str) -> Item:
        async with self._sessions() as session:
            row = await session.get(ItemRow, item_id)
        if row is None:
            raise NotFound(item_id)
        return _item(row)

    async def list_by_ids(self, ids: list[str]) -> list[Item]:
        """One query for the whole set (no N+1), always bounded."""
        query = (
            select(ItemRow)
            .where(ItemRow.id.in_(ids))
            .order_by(ItemRow.created_at.desc())
            .limit(500)
        )
        async with self._sessions() as session:
            rows = (await session.scalars(query)).all()
        return [_item(row) for row in rows]

    async def upsert(self, item: Item) -> None:
        """Idempotent: a replay converges on one row.

        The insert construct is dialect specific (PostgreSQL and SQLite
        shown); MySQL has on_duplicate_key_update.
        """
        dialect = self._engine.dialect.name
        insert = (
            postgresql.insert if dialect == "postgresql" else sqlite.insert
        )
        statement = insert(ItemRow).values(
            id=item.id, name=item.name, created_at=item.created_at
        )
        statement = statement.on_conflict_do_update(
            index_elements=[ItemRow.id], set_={"name": statement.excluded.name}
        )
        async with self._sessions() as session, session.begin():
            await session.execute(statement)

    async def rename_all(self, old: str, new: str) -> int:
        """One transaction per business operation.

        session.begin() commits, or rolls back when the block raises.
        """
        async with self._sessions() as session, session.begin():
            result = await session.execute(
                update(ItemRow).where(ItemRow.name == old).values(name=new)
            )
        return result.rowcount

    async def count_by_name(self, name: str) -> int:
        """The raw SQL escape hatch, for queries unreadable as a builder."""
        query = text(
            """
            SELECT count(*)
            FROM items
            WHERE name = :name
            """
        )
        async with self._engine.connect() as conn:
            return (await conn.execute(query, {"name": name})).scalar_one()


def _row(item: Item) -> ItemRow:
    return ItemRow(id=item.id, name=item.name, created_at=item.created_at)


def _item(row: ItemRow) -> Item:
    created = row.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    return Item(id=row.id, name=row.name, created_at=created.astimezone(UTC))
