"""GET /healthz, the one health endpoint of the service (api-contract skill).
It is not versioned: it reports every API version in `api_versions`.

Always public (no token), never cached, and every field is always present.
`config` is an allowlist of non-secret values: add a key on purpose, never
dump the environment, a DSN or a secret. `checks` holds one entry per
dependency the service cannot work without; an optional dependency is not a
check. Any failed check makes the status "down" and the response 503. A
check reports a short code ("timeout", "unavailable"), never the exception
text; the cause is logged.
"""

from __future__ import annotations

import asyncio
import logging
import socket
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from litestar import Request, Response, get
from litestar.openapi import ResponseSpec
from msgspec import Struct

from .. import deps
from ..versions import API_VERSIONS

log = logging.getLogger("service.api.health")
CHECK_TIMEOUT_SECONDS = 2


class Check(Struct):
    name: str
    status: str
    latency_ms: float
    error: str


class Healthz(Struct, kw_only=True):
    status: str
    service_name: str
    env_name: str
    node_name: str
    api_versions: list[str]
    service_version: str
    started_at: datetime
    checked_at: datetime
    uptime_seconds: int
    config: dict[str, str | int | float | bool | list[str]]
    checks: list[Check]


class InternalHealthz(Healthz, kw_only=True):
    """`/healthz` plus who the caller says it is."""

    caller: deps.Caller


def _answer(body: Healthz) -> Response:
    status_code = 200 if body.status == "ok" else 503
    return Response(
        body, status_code=status_code, headers={"Cache-Control": "no-store"}
    )


@get(
    "/internal",
    operation_id="internal_health",
    summary="Health of the service for an internal caller",
    tags=["internal"],
    guards=[deps.require_internal_token],
    responses={503: ResponseSpec(InternalHealthz, description="down")},
)
async def internal_health(request: Request) -> Response[InternalHealthz]:
    """`/internal`: the health body behind the service token, plus `caller`.

    200 proves the token works and shows the identity this service received;
    401 means the token is missing or wrong.
    """
    base = await build(request)
    fields = {name: getattr(base, name) for name in base.__struct_fields__}
    caller = deps.caller(request)
    return _answer(InternalHealthz(**fields, caller=caller))


@get(
    "/healthz",
    operation_id="healthz",
    summary="Health of the service",
    tags=["health"],
    responses={503: ResponseSpec(Healthz, description="down")},
)
async def healthz(request: Request) -> Response[Healthz]:
    """The one health route, `/healthz`, at the root next to `/docs`."""
    return _answer(await build(request))


async def build(request: Request) -> Healthz:
    state = request.app.state
    settings = state.settings
    now = datetime.now(UTC)
    checks = await run_checks(state.checks)
    down = any(check.status != "ok" for check in checks)
    return Healthz(
        status="down" if down else "ok",
        service_name=settings.service_name,
        env_name=settings.env_name,
        node_name=settings.node_name or socket.gethostname(),
        api_versions=list(API_VERSIONS),
        service_version=settings.service_version,
        started_at=state.started_at,
        checked_at=now,
        uptime_seconds=int((now - state.started_at).total_seconds()),
        config=public_config(settings),
        checks=checks,
    )


def public_config(settings) -> dict:
    """The non-secret settings worth seeing during an incident."""
    return {
        "port": settings.http_port,
        "log_level": settings.log_level,
        "docs_url": "/docs",
    }


async def run_checks(
    pings: dict[str, Callable[[], Awaitable[None]]],
) -> list[Check]:
    return list(
        await asyncio.gather(*(run_check(n, p) for n, p in pings.items()))
    )


async def run_check(name: str, ping: Callable[[], Awaitable[None]]) -> Check:
    start = time.perf_counter()
    error = ""
    try:
        await asyncio.wait_for(ping(), timeout=CHECK_TIMEOUT_SECONDS)
    except TimeoutError:
        error = "timeout"
    except Exception:
        error = "unavailable"
        log.warning("health check failed: %s", name, exc_info=True)
    return Check(
        name=name,
        status="down" if error else "ok",
        latency_ms=round((time.perf_counter() - start) * 1000, 1),
        error=error,
    )
