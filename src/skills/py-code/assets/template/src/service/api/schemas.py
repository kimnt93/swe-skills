"""JSON contract types (also the OpenAPI source): `msgspec.Struct`, no
pydantic. msgspec validates and decodes at the API edge; the domain validates
its rules.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from msgspec import Meta, Struct


class CreateItemRequest(Struct, kw_only=True):
    name: Annotated[str, Meta(examples=["pen"])]


class ItemResponse(Struct):
    id: str
    name: str
    created_at: datetime


class ErrorBody(Struct, frozen=True):
    code: str = ""
    retryable: bool = False


class Envelope(Struct, kw_only=True):
    """The same envelope as the Go and Rust services: one contract.

    Every field is always present with its zero value (`data` null,
    `error` {"code": "", "retryable": false}): nothing is omitted, so
    clients never branch on absence.
    """

    success: bool
    status_code: int
    message: str = ""
    data: Any | None = None
    error: ErrorBody = ErrorBody()
