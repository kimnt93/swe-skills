"""Pure domain: no I/O, no framework, no logging, no clock reads (inject
`now`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


class InvalidNameError(ValueError):
    """The item name is empty or longer than 120 characters."""


class NotFoundError(LookupError):
    """The resource does not exist (or is not visible to the caller)."""


@dataclass(frozen=True, slots=True)
class Item:
    id: str
    name: str
    created_at: datetime

    @classmethod
    def create(cls, id: str, name: str, now: datetime) -> Item:
        name = name.strip()
        if not 1 <= len(name) <= 120:
            raise InvalidNameError("item name must be 1-120 characters")
        return cls(id=id, name=name, created_at=now.astimezone(UTC))
