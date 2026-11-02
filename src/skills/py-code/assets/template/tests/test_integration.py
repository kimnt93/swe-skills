"""Real PostgreSQL, Redis and Kafka (disposable containers). Run:

docker compose -f docker-compose.infra.local.yaml up -d postgres redis kafka
scripts/health.sh --wait postgres,redis,kafka
set -a; . ./.env; set +a; uv run pytest -m integration -o addopts=""
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from pathlib import Path

import psycopg
import pytest

from service.db.postgres import PostgresItems
from service.db.redis import RedisClient
from service.db.s3 import ObjectNotFoundError, ObjectStore
from service.domain.item import Item, NotFoundError
from service.messaging.kafka import KafkaPublisher, consume
from service.settings import Settings, SettingsError

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def settings() -> Settings:
    try:
        return Settings()
    except SettingsError as exc:
        pytest.skip(f"integration environment not configured: {exc}")


def goose_up(sql_file: Path, conninfo: str) -> None:
    """Apply the goose Up section (the real service runs the goose binary as a
    one-shot job).
    """
    up = (
        sql_file.read_text()
        .split("-- +goose Up")[1]
        .split("-- +goose Down")[0]
    )
    with psycopg.connect(conninfo, autocommit=True) as conn:
        conn.execute("DROP TABLE IF EXISTS items")
        conn.execute(up)


async def test_postgres_round_trip(settings):
    goose_up(
        Path(__file__).parents[1] / "schemas" / "0001_items.sql",
        settings.postgres_conninfo,
    )
    repo = await PostgresItems.open(settings)
    try:
        item = Item.create(str(uuid.uuid4()), "pen", datetime.now(UTC))
        await repo.create(item)
        got = await repo.get(item.id)
        assert (
            got.name == "pen"
            and got.created_at.utcoffset().total_seconds() == 0
        )
        with pytest.raises(NotFoundError):
            await repo.get(str(uuid.uuid4()))
        other = Item.create(str(uuid.uuid4()), "ruler", datetime.now(UTC))
        await repo.upsert(other)
        await repo.upsert(other)  # idempotent
        assert len(await repo.list_by_ids([item.id, other.id])) == 2
        assert await repo.claim_oldest() is not None
    finally:
        await repo.close()


async def test_redis_lock_is_exclusive(settings):
    redis = RedisClient(settings)
    try:
        key = f"lock:{uuid.uuid4()}"
        release = await redis.lock(key, 5)
        assert release is not None
        assert await redis.lock(key, 5) is None, (
            "a second holder must not get the lock"
        )
        await release()
        assert await redis.lock(key, 5) is not None
    finally:
        await redis.close()


async def test_kafka_publish_consume(settings):
    topic = f"e2e.{uuid.uuid4()}"
    settings = settings.model_copy(
        update={"kafka_consumer_group": f"e2e-{uuid.uuid4()}"}
    )
    pub = KafkaPublisher(settings)
    stop, got = asyncio.Event(), asyncio.Queue()
    try:
        await pub.publish(
            topic,
            "seed",
            b"seed",
            # create the topic first: late topics are noticed only after a
            # metadata refresh
        )

        async def handler(msg):
            await got.put((msg.key(), msg.value()))
            stop.set()

        task = asyncio.create_task(consume(settings, [topic], handler, stop))
        for _ in range(30):
            await pub.publish(topic, "k", b"v")
            try:
                assert await asyncio.wait_for(got.get(), 2) == (b"k", b"v")
                break
            except TimeoutError:
                continue
        else:
            pytest.fail("no message consumed")
        await asyncio.wait_for(task, 10)
    finally:
        pub.close()


async def test_s3_round_trip(settings):
    store = ObjectStore(settings)
    await store.ensure_bucket()
    await store.ping()
    prefix = f"e2e/{uuid.uuid4()}/"
    await store.put(prefix + "a.json", b'{"a": 1}')
    assert await store.get(prefix + "a.json") == b'{"a": 1}'
    assert await store.list(prefix, 10) == [prefix + "a.json"]
    with pytest.raises(ObjectNotFoundError):
        await store.get(prefix + "missing")
    await store.delete(prefix + "a.json")
