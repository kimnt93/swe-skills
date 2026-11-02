"""Thin routes: validate at the edge, call one use case, answer through the
envelope. No SQL, no rules.
"""

from __future__ import annotations

from litestar import Response, get, post
from litestar.di import NamedDependency
from litestar.openapi import ResponseSpec
from litestar.params import FromPath, JSONBody

from ...application.items import Items
from .. import envelope, schemas

TAGS = ["items"]


@post(
    "/v1/items",
    status_code=201,
    tags=TAGS,
    responses={422: ResponseSpec(schemas.Envelope, description="invalid")},
)
async def create_item(
    data: JSONBody[schemas.CreateItemRequest],
    svc: NamedDependency[Items],
) -> Response:
    item = await svc.create(data.name)
    return envelope.ok(
        schemas.ItemResponse(
            id=item.id, name=item.name, created_at=item.created_at
        ),
        201,
        "item created",
    )


@get(
    "/v1/items/{item_id:str}",
    tags=TAGS,
    responses={404: ResponseSpec(schemas.Envelope, description="not found")},
)
async def get_item(
    item_id: FromPath[str], svc: NamedDependency[Items]
) -> Response:
    item = await svc.get(item_id)
    return envelope.ok(
        schemas.ItemResponse(
            id=item.id, name=item.name, created_at=item.created_at
        )
    )


handlers = [create_item, get_item]
