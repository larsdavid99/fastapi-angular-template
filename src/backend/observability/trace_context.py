"""Trace context — what ties log lines, spans and audit records together."""

import structlog
from opentelemetry.trace import Span

# The span attribute and structlog key holding the work's correlation ID.
CORRELATION_ID = "correlation_id"


def bind_trace_id(span: Span) -> None:
    """Put span's trace ID on the log lines that follow, unless one is bound."""
    span_context = span.get_span_context()
    if (
        span_context.is_valid
        and "trace_id" not in structlog.contextvars.get_contextvars()
    ):
        structlog.contextvars.bind_contextvars(
            trace_id=format(span_context.trace_id, "032x")
        )
