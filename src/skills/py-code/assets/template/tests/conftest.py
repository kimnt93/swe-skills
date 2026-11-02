from __future__ import annotations

from datetime import UTC, datetime

import pytest
from litestar.testing import TestClient

from service.api.app import create_app
from service.application.items import Items
from service.domain.item import Item, NotFoundError
from service.settings import Settings

BASE_ENV = {
    "SERVICE_NAME": "svc",
    "INTERNAL_SERVICE_TOKEN": "tok",
    "POSTGRES_HOST": "pg",
    "POSTGRES_DB": "db",
    "POSTGRES_USER": "u",
    "POSTGRES_PASSWORD": "p",
    "REDIS_HOST": "r",
    "REDIS_PASSWORD": "p",
    "KAFKA_BOOTSTRAP_SERVERS": "k:9092",
    "KAFKA_CONSUMER_GROUP": "g",
    "S3_ENDPOINT": "http://s3:9000",
    "S3_BUCKET": "b",
    "S3_ACCESS_KEY": "a",
    "S3_SECRET_KEY": "s",
}


@pytest.fixture
def env(monkeypatch):
    for key, value in BASE_ENV.items():
        monkeypatch.setenv(key, value)
    return monkeypatch


class FakeRepo:
    def __init__(self) -> None:
        self.items: dict[str, Item] = {}

    async def create(self, item: Item) -> None:
        self.items[item.id] = item

    async def get(self, id: str) -> Item:
        try:
            return self.items[id]
        except KeyError:
            raise NotFoundError(id) from None


class FakeEvents:
    def __init__(self) -> None:
        self.published: list[tuple[str, str, bytes]] = []

    async def publish(self, topic: str, key: str, value: bytes) -> None:
        self.published.append((topic, key, value))


@pytest.fixture
def events() -> FakeEvents:
    return FakeEvents()


@pytest.fixture
def client(env, events):
    svc = Items(
        repo=FakeRepo(),
        events=events,
        new_id=lambda: "id-1",
        now=lambda: datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
    )
    with TestClient(create_app(Settings(), items_service=svc)) as c:
        yield c
