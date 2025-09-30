from __future__ import annotations

from fastapi import HTTPException

from .schemas import APIError


def format_http_exception(exc: HTTPException) -> APIError:
    return APIError(
        type="http_error",
        message=exc.detail if isinstance(exc.detail, str) else str(exc.detail),
        details={"status_code": exc.status_code},
    )


def format_unhandled_exception(exc: Exception) -> APIError:
    return APIError(type="internal_server_error", message=str(exc), details=None)


__all__ = ["format_http_exception", "format_unhandled_exception"]
