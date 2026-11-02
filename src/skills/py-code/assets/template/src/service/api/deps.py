"""Request dependencies: the use cases from app.state, shared-token
authentication and the caller identity (api-contract skill, "Internal calls").
"""

from __future__ import annotations

import hmac

from litestar import Request
from litestar.connection import ASGIConnection
from litestar.handlers import BaseRouteHandler
from msgspec import Struct

from ..application.items import Items
from .envelope import ApiError


def items(request: Request) -> Items:
    return request.app.state.use_cases


class Caller(Struct):
    """Who the calling service says it acts for. Only meaningful after the
    token check; "" when the header is absent.
    """

    user_id: str
    username: str


def bare_token(value: str) -> str:
    """The token without an optional `Bearer ` prefix (both forms work)."""
    value = value.strip()
    if value[:7].lower() == "bearer ":
        value = value[7:].strip()
    return value


def require_internal_token(
    connection: ASGIConnection, _: BaseRouteHandler | None = None
) -> None:
    """Constant-time compare; never log the token. 401 before any identity
    header is trusted. Used as a guard of a router or a handler.
    """
    secret = connection.app.state.settings.internal_service_token
    want = secret.get_secret_value()
    got = bare_token(connection.headers.get("x-internal-service-token", ""))
    if not want or not hmac.compare_digest(got.encode(), want.encode()):
        raise ApiError(401, "unauthorized", "missing or invalid service token")


def caller(request: Request) -> Caller:
    """`x-user-id` / `x-username`, trimmed and capped at 128 characters."""
    return Caller(
        user_id=request.headers.get("x-user-id", "").strip()[:128],
        username=request.headers.get("x-username", "").strip()[:128],
    )
