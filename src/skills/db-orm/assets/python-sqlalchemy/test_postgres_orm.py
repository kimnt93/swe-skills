"""Live test for the SQLAlchemy adapter (needs the items table from goose).

set -a; . ./.env; set +a; uv run pytest -m integration -o addopts=""
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from service.db.postgres_orm import OrmItems
from service.domain.item import Item, NotFoundError
from service.settings import PostgresSettings, SettingsError

pytestmark = pytest.mark.integration


async def test_orm_round_trip():
    try:
        settings = PostgresSettings()
    except SettingsError:
        pytest.skip("integration environment not configured")

    repo = OrmItems.open(settings)
    try:
        await repo.ping()

        item = Item.create(str(uuid.uuid4()), "pen", datetime.now(UTC))
        await repo.create(item)

        got = await repo.get(item.id)
        assert got.name == "pen"
        assert got.created_at.utcoffset().total_seconds() == 0

        with pytest.raises(NotFoundError):
            await repo.get(str(uuid.uuid4()))

        assert [i.id for i in await repo.list_by_ids([item.id])] == [item.id]
        assert await repo.rename_all("pen", "pencil") >= 1
        assert (await repo.get(item.id)).name == "pencil"
    finally:
        await repo.close()
