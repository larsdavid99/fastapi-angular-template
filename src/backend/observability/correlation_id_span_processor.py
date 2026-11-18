"""Correlation ID Span Processor — every span carries its work's ID (ADR-0002)."""

import structlog
from opentelemetry.context import Context
from opentelemetry.sdk.trace import Span, SpanProcessor

from observability.trace_context import CORRELATION_ID


class CorrelationIdSpanProcessor(SpanProcessor):
    """
    Copies the correlation ID bound to structlog onto each span as it starts,
    so a span can be found by the same ID as its log lines and audit records.
    The request's own server span starts before the ID is bound;
    CorrelationIdMiddleware tags that one.
    """

    def on_start(self, span: Span, parent_context: Context | None = None) -> None:
        correlation_id = structlog.contextvars.get_contextvars().get(CORRELATION_ID)
        if correlation_id:
            span.set_attribute(CORRELATION_ID, str(correlation_id))
