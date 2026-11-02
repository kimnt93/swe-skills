"""Ports: what the use cases need from the outside, declared where they are
used (small Protocols).
"""

from __future__ import annotations

from typing import Protocol

from ..domain.item import Item


class ItemRepository(Protocol):
    async def create(self, item: Item) -> None: ...

    async def get(self, id: str) -> Item:
        """Raise `NotFoundError` when absent."""
        ...


class EventPublisher(Protocol):
    async def publish(self, topic: str, key: str, value: bytes) -> None: ...
