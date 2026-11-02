"""Use cases: flow and validation; no SQL, no HTTP."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

import msgspec

from ..domain.item import Item
from .ports import EventPublisher, ItemRepository


class ItemCreated(msgspec.Struct, frozen=True):
    """Event payload: a typed struct encodes straight to JSON bytes (msgspec),
    no dict round trip.
    """

    id: str
    name: str


@dataclass(slots=True)
class Items:
    repo: ItemRepository
    events: EventPublisher
    new_id: Callable[[], str]
    now: Callable[[], datetime]

    async def create(self, name: str) -> Item:
        item = Item.create(self.new_id(), name, self.now())
        await self.repo.create(item)
        await self.events.publish(
            "items.created",
            item.id,
            msgspec.json.encode(ItemCreated(item.id, item.name)),
        )
        return item

    async def get(self, id: str) -> Item:
        return await self.repo.get(id)
