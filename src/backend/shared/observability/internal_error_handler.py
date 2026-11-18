"""Internal Error Handler — the 500 for unhandled exceptions, with the request's ID."""

import structlog
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from shared.observability.correlation_id_middleware import CorrelationIdMiddleware


async def internal_error_handler(request: Request, exc: Exception) -> PlainTextResponse:
    """Registered for Exception, so Starlette's ServerErrorMiddleware calls it."""
    correlation_id = structlog.contextvars.get_contextvars().get("correlation_id")
    headers = {CorrelationIdMiddleware.HEADER: correlation_id} if correlation_id else {}
    return PlainTextResponse("Internal Server Error", status_code=500, headers=headers)
