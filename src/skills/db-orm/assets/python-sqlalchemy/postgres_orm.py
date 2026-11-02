"""Optional SQLAlchemy 2 adapter for the items port.

Use it only when the project asks for an ORM or already has one. The default
adapter is plain SQL (py-code/references/postgres.md). Copy this file next to
the raw adapter as `service/db/postgres_orm.py`; both satisfy ItemRepository.

Needs: sqlalchemy[asyncio]>=2.0 and psycopg[binary]>=3.2 (the driver the raw
adapter already uses). The schema stays in goose files (db-migrations): never
call `Base.metadata.create_all` against a real database.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Uuid, select, text, update
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from ..domain.item import Item, NotFoundError
from ..settings import PostgresSettings


class Base(DeclarativeBase):
    pass


class ItemRow(Base):
    """Maps the `items` table. A row is not a domain type: see _to_item."""

    __tablename__ = "items"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    name: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def _to_item(row: ItemRow) -> Item:
    return Item(id=row.id, name=row.name, created_at=row.created_at)


def _to_row(item: Item) -> ItemRow:
    return ItemRow(id=item.id, name=item.name, created_at=item.created_at)


class OrmItems:
    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine
        # expire_on_commit=False: rows stay readable after commit, and no
        # lazy load can fire later (a lazy load in async code raises).
        self.sessions = async_sessionmaker(engine, expire_on_commit=False)

    @classmethod
    def open(
        cls, settings: PostgresSettings, *, pool_size: int = 10
    ) -> OrmItems:
        url = URL.create(
            "postgresql+psycopg",
            username=settings.postgres_user,
            password=settings.postgres_password.get_secret_value(),
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=settings.postgres_db,
            query={"sslmode": settings.postgres_sslmode},
        )
        engine = create_async_engine(
            url,
            pool_size=pool_size,
            pool_pre_ping=True,
        )
        return cls(engine)

    async def close(self) -> None:
        await self.engine.dispose()

    async def ping(self) -> None:
        async with self.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

    async def create(self, item: Item) -> None:
        # One transaction per operation: begin() commits on success and
        # rolls back on error.
        async with self.sessions() as session, session.begin():
            session.add(_to_row(item))

    async def get(self, id: str) -> Item:
        async with self.sessions() as session:
            row = await session.get(ItemRow, id)

        if row is None:
            raise NotFoundError(f"item {id}")

        return _to_item(row)

    async def list_by_ids(self, ids: list[str]) -> list[Item]:
        """One query for a set (no N+1), bounded."""
        if not ids:
            return []

        statement = (
            select(ItemRow)
            .where(ItemRow.id.in_(ids))
            .order_by(ItemRow.created_at.desc())
            .limit(500)
        )
        async with self.sessions() as session:
            rows = (await session.scalars(statement)).all()

        return [_to_item(row) for row in rows]

    async def rename_all(self, old: str, new: str) -> int:
        statement = update(ItemRow).where(ItemRow.name == old).values(name=new)
        async with self.sessions() as session, session.begin():
            result = await session.execute(statement)

        return result.rowcount
