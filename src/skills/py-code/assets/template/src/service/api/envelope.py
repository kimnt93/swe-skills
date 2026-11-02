"""Response envelope and error mapping. Handlers answer only through these
helpers.
"""

from __future__ import annotations

import logging
from typing import Any

from litestar import Request, Response
from litestar.exceptions import HTTPException, ValidationException

from ..domain.item import InvalidNameError, NotFoundError
from . import schemas

log = logging.getLogger("service.api")

_CODES = {
    400: "invalid_request",
    401: "unauthorized",
    404: "not_found",
    405: "method_not_allowed",
    422: "validation_error",
}


class ApiError(Exception):
    """A business rejection: HTTP status, stable machine code (add codes, never
    rename), safe message.
    """

    def __init__(
        self, status: int, code: str, message: str, retryable: bool = False
    ) -> None:
        super().__init__(message)
        self.status, self.code, self.message, self.retryable = (
            status,
            code,
            message,
            retryable,
        )


def to_api_error(exc: Exception) -> ApiError | None:
    if isinstance(exc, ApiError):
        return exc
    if isinstance(exc, InvalidNameError):
        return ApiError(422, "validation_error", str(exc))
    if isinstance(exc, NotFoundError):
        return ApiError(404, "not_found", "resource not found")
    if isinstance(exc, ValidationException):
        return ApiError(
            400, "invalid_request", "request body or parameters are invalid"
        )
    if isinstance(exc, HTTPException):
        code = _CODES.get(exc.status_code, "error")
        return ApiError(exc.status_code, code, str(exc.detail))
    return None


def ok(data: Any, status: int = 200, message: str = "") -> Response:
    # nothing is omitted: every envelope field is always present; msgspec
    # encodes datetime/UUID natively, several times faster than stdlib json
    body = schemas.Envelope(
        success=True, status_code=status, message=message, data=data
    )
    return Response(body, status_code=status)


def failure(err: ApiError) -> Response:
    body = schemas.Envelope(
        success=False,
        status_code=err.status,
        message=err.message,
        error=schemas.ErrorBody(code=err.code, retryable=err.retryable),
    )
    return Response(body, status_code=err.status)


def api_error_handler(_: Request, exc: Exception) -> Response:
    return failure(
        to_api_error(exc) or ApiError(500, "internal_error", "internal error")
    )


def unhandled_handler(_: Request, exc: Exception) -> Response:
    # Log the cause; return nothing about it: infrastructure errors can carry
    # DSNs, SQL or payloads.
    log.error("unhandled error", exc_info=exc)
    return failure(ApiError(500, "internal_error", "internal error"))
