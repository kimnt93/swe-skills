"""Kafka adapter (confluent-kafka): durable async producer and a manual-commit
consumer loop.

confluent-kafka is synchronous. The producer polls on a background thread and
resolves an asyncio Future from the
delivery callback, so `await publish(...)` returns only when the broker
acknowledged the message.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Awaitable, Callable

from confluent_kafka import (
    Consumer,
    KafkaError,
    KafkaException,
    Message,
    Producer,
)

from ..settings import KafkaSettings


class KafkaPublisher:
    def __init__(self, settings: KafkaSettings) -> None:
        self._p = Producer(
            {
                **settings.kafka_client_config(),
                "enable.idempotence": True,  # retries cannot duplicate
                "acks": "all",
                "linger.ms": 5,
                "compression.type": "lz4",
            }
        )
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._poll, name="kafka-poll", daemon=True
        )
        self._thread.start()

    def _poll(self) -> None:
        while not self._stop.is_set():
            self._p.poll(0.1)

    async def publish(
        self,
        topic: str,
        key: str,
        value: bytes,
        headers: dict[str, str] | None = None,
    ) -> None:
        loop = asyncio.get_running_loop()
        done: asyncio.Future[None] = loop.create_future()

        def on_delivery(err: KafkaError | None, _msg: Message) -> None:
            if err is not None:
                loop.call_soon_threadsafe(
                    done.set_exception, KafkaException(err)
                )
            else:
                loop.call_soon_threadsafe(done.set_result, None)

        self._p.produce(
            topic,
            value=value,
            key=key,
            headers=list((headers or {}).items()),
            on_delivery=on_delivery,
        )
        await done

    def ping(self) -> None:
        self._p.list_topics(timeout=3)

    def close(self) -> None:
        """Drain queued messages (bounded), then stop polling."""
        self._p.flush(10)
        self._stop.set()
        self._thread.join(timeout=2)


Handler = Callable[[Message], Awaitable[None]]


async def consume(
    settings: KafkaSettings,
    topics: list[str],
    handler: Handler,
    stop: asyncio.Event,
) -> None:
    """At-least-once: commit only after the handler succeeds, so handlers must
    be idempotent.

    Subscribe to topics that already exist: a topic created later is not
    noticed until the next metadata refresh.
    """
    consumer = Consumer(
        {
            **settings.kafka_client_config(),
            "group.id": settings.kafka_consumer_group,
            "enable.auto.commit": False,
            "auto.offset.reset": "latest",
        }
    )
    consumer.subscribe(topics)
    loop = asyncio.get_running_loop()
    try:
        while not stop.is_set():
            msg = await loop.run_in_executor(
                None, consumer.poll, 0.5
            )  # poll blocks: keep it off the event loop
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                raise KafkaException(msg.error())
            await handler(msg)
            consumer.commit(message=msg, asynchronous=False)
    finally:
        # leave the group cleanly: a restart does not wait for the session
        # timeout
        consumer.close()
