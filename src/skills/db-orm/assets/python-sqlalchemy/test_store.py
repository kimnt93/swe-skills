"""Adapter tests.

With POSTGRES_HOST set they run against PostgreSQL (schema from the goose
files); otherwise against in-memory SQLite, so the same tests prove the
adapter on two databases.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text, update
from sqlalchemy.engine import URL
from store import Item, ItemRow, NotFound, Store

DDL = """
CREATE TABLE IF NOT EXISTS items (
    id         char(32) PRIMARY KEY,
    name       text NOT NULL,
    created_at timestamp NOT NULL
)
"""


def open_store() -> Store:
    host = os.environ.get("POSTGRES_HOST")
    if host:
        url = URL.create(
            "postgresql+asyncpg",
            username=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"],
            host=host,
            port=int(os.environ["POSTGRES_PORT"]),
            database=os.environ["POSTGRES_DB"],
        )
        return Store.open(url.render_as_string(hide_password=False))
    return Store.open("sqlite+aiosqlite:///:memory:")


async def ready() -> Store:
    store = open_store()
    if not os.environ.get("POSTGRES_HOST"):
        async with store._engine.begin() as conn:
            await conn.execute(text(DDL))
    return store


def run(coro):
    return asyncio.run(coro)


def test_round_trip_upsert_list_rename_count():
    async def scenario():
        store = await ready()
        try:
            await store.ping()
            item_id = str(uuid.uuid4())
            created = datetime.now(UTC).replace(microsecond=0)
            item = Item(item_id, "pen", created)
            await store.create(item)

            got = await store.get(item_id)
            assert got.name == "pen" and got.created_at == created
            assert got.created_at.tzinfo is not None

            with pytest.raises(NotFound):
                await store.get(str(uuid.uuid4()))

            changed = Item(item_id, "pencil", created)
            await store.upsert(changed)
            await store.upsert(changed)
            listed = await store.list_by_ids([item_id])
            assert [i.name for i in listed] == ["pencil"]

            assert await store.rename_all("pencil", "marker") >= 1
            assert await store.count_by_name("marker") >= 1
        finally:
            await store.close()

    run(scenario())


def test_transaction_rolls_back_on_error():
    async def scenario():
        store = await ready()
        try:
            item_id = str(uuid.uuid4())
            created = datetime.now(UTC).replace(microsecond=0)
            await store.create(Item(item_id, "before", created))

            class Boom(Exception):
                pass

            with pytest.raises(Boom):
                async with store._sessions() as session, session.begin():
                    await session.execute(
                        update(ItemRow)
                        .where(ItemRow.id == item_id)
                        .values(name="inside")
                    )
                    raise Boom()

            assert (await store.get(item_id)).name == "before"
        finally:
            await store.close()

    run(scenario())
