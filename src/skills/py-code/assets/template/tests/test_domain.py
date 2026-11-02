from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from service.domain.item import InvalidNameError, Item

NOW = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone(timedelta(hours=7)))


def test_create_trims_and_normalises_to_utc():
    item = Item.create("1", "  pen ", NOW)
    assert (
        item.name == "pen"
        and item.created_at.tzinfo is UTC
        and item.created_at.hour == 20
    )


@pytest.mark.parametrize("name", ["", "   ", "x" * 121])
def test_invalid_names(name):
    with pytest.raises(InvalidNameError):
        Item.create("1", name, NOW)
