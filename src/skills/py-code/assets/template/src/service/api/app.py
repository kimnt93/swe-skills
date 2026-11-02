"""Application factory (Litestar: msgspec models, no pydantic).

    uvicorn service.api.app:create_app --factory --host 0.0.0.0 --port 3000
    --proxy-headers

Dependencies are built once in the lifespan (or passed in by tests) and held on
app.state; the routes never construct adapters. Middleware: the request log
wraps routing, guards and validation.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from litestar import Litestar, Router
from litestar.di import Provide
from litestar.exceptions import HTTPException
from litestar.openapi import OpenAPIConfig
from litestar.openapi.plugins import SwaggerRenderPlugin

from .. import __version__
from ..application.items import Items
from ..domain.item import InvalidNameError, NotFoundError
from ..settings import Settings, get_settings
from . import deps, envelope
from .routes import health, items

log = logging.getLogger("service.api")


def create_app(
    settings: Settings | None = None,
    *,
    items_service: Items | None = None,
    checks: dict | None = None,
) -> Litestar:
    """Tests pass `items_service` (with fakes) and `checks`; production builds
    real adapters in the lifespan.
    """
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: Litestar):
        closers: list[Callable] = []
        if items_service is None:
            from ..db.postgres import PostgresItems
            from ..db.redis import RedisClient
            from ..db.s3 import ObjectStore
            from ..messaging.kafka import KafkaPublisher

            db = await PostgresItems.open(settings)
            redis = RedisClient(settings)
            kafka = KafkaPublisher(settings)
            objects = ObjectStore(settings)
            app.state.use_cases = Items(
                repo=db,
                events=kafka,
                new_id=lambda: str(uuid.uuid4()),
                now=lambda: datetime.now(UTC),
            )
            app.state.checks = {
                "postgres": db.ping,
                "redis": redis.ping,
                "kafka": _async(kafka.ping),
                "s3": objects.ping,
            }
            closers += [db.close, redis.close, _async(kafka.close)]
        try:
            yield
        finally:
            for close in reversed(closers):
                await close()

    # Domain failures are registered explicitly. Anything unregistered is a
    # bug: logged, and a generic 500 (never its message).
    handlers = {
        exc_type: envelope.api_error_handler
        for exc_type in (
            envelope.ApiError,
            InvalidNameError,
            NotFoundError,
            HTTPException,  # includes the framework's 400 and 404
        )
    }
    handlers[Exception] = envelope.unhandled_handler

    v1 = Router(
        "/",
        route_handlers=[*items.handlers],
        guards=[deps.require_internal_token],
    )
    app = Litestar(
        route_handlers=[health.healthz, health.internal_health, v1],
        dependencies={"svc": Provide(deps.items, sync_to_thread=False)},
        exception_handlers=handlers,
        middleware=[_RequestLog],
        openapi_config=OpenAPIConfig(
            title=settings.service_name,
            version=__version__,
            path="/docs",  # /docs is Swagger UI, /docs/openapi.json the spec
            render_plugins=[SwaggerRenderPlugin()],
        ),
        lifespan=[lifespan],
        logging_config=None,  # observability/service_logging.py owns logs
    )
    app.state.settings = settings
    app.state.started_at = datetime.now(UTC)
    app.state.use_cases = items_service
    app.state.checks = checks or {}
    return app


class _RequestLog:
    """One `request completed` line per request: pure ASGI, so it sees every
    response, including errors."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        start = time.perf_counter()
        status = {"code": 500}

        async def wrapped(message) -> None:
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, wrapped)
        finally:
            code = status["code"]
            level = (
                logging.ERROR
                if code >= 500
                else logging.WARNING
                if code >= 400
                else logging.INFO
            )
            log.log(
                level,
                "request completed",
                extra={
                    "fields": {
                        "method": scope.get("method"),
                        # the template, not the raw URL
                        "path": scope.get("path_template", "unmatched"),
                        "status_code": code,
                        "duration_ms": round(
                            (time.perf_counter() - start) * 1000, 2
                        ),
                    }
                },
            )


def _async(fn: Callable) -> Callable:
    async def run() -> None:
        fn()

    return run
