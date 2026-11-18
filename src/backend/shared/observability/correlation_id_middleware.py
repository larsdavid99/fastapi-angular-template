"""Correlation ID Middleware — binds one ID per inbound request to all its logs."""

import re
import time
import uuid

import structlog
from opentelemetry import trace
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from shared.observability.request_context import RequestContext
from shared.observability.trace_context import CORRELATION_ID, bind_trace_id

logger = structlog.get_logger(__name__)


class CorrelationIdMiddleware:
    """
    Reuses a well-formed incoming X-Correlation-ID or generates one, binds it to
    structlog's context for the request, echoes it on the response, and logs
    the request's outcome.

    Unhandled exceptions are logged here and re-raised, so Starlette's outer
    ServerErrorMiddleware still answers them (with internal_error_handler, which
    puts the ID on the 500). The ID stays bound after the request so that answer
    and the server's own error log still see it. The server runs each request in
    its own task, so the binding never reaches another request, and anything an
    outer layer bound (e.g. a trace ID) is kept.
    """

    HEADER = "X-Correlation-ID"
    _VALID_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        context = self._start(scope)
        send_with_id = self._echo_id(send, context)
        try:
            await self.app(scope, receive, send_with_id)
        except Exception:
            logger.exception("request.failed")
            context.status = context.status or 500  # ServerErrorMiddleware answers
            raise
        finally:
            self._log_outcome(context)

    def _start(self, scope: Scope) -> RequestContext:
        context = RequestContext(
            correlation_id=self._resolve_id(scope),
            method=scope["method"],
            path=scope["path"],
            started=time.perf_counter(),
        )
        structlog.contextvars.bind_contextvars(correlation_id=context.correlation_id)
        self._tag_request_span(context.correlation_id)
        return context

    def _tag_request_span(self, correlation_id: str) -> None:
        """The request's server span started before the ID existed; tag it here."""
        span = trace.get_current_span()
        span.set_attribute(CORRELATION_ID, correlation_id)
        bind_trace_id(span)

    def _echo_id(self, send: Send, context: RequestContext) -> Send:
        """Wrap send to add the ID header and record the response status."""

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                context.status = message["status"]
                MutableHeaders(scope=message)[self.HEADER] = context.correlation_id
            await send(message)

        return send_with_id

    def _resolve_id(self, scope: Scope) -> str:
        incoming = Headers(scope=scope).get(self.HEADER)
        if incoming and self._VALID_ID.fullmatch(incoming):
            return incoming
        return str(uuid.uuid4())

    def _log_outcome(self, context: RequestContext) -> None:
        """Log completion, or an abort when no response was ever started."""
        fields = {
            "method": context.method,
            "path": context.path,
            "duration_ms": round((time.perf_counter() - context.started) * 1000, 1),
        }
        if context.status is None:
            logger.warning("request.aborted", **fields)
        else:
            logger.info("request.completed", status=context.status, **fields)
