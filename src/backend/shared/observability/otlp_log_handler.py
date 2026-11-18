"""OTLP Log Handler — hands each log line to OpenTelemetry for Loki (ADR-0002)."""

import logging

from opentelemetry.instrumentation.logging.handler import LoggingHandler
from opentelemetry.sdk._logs import LoggerProvider

from shared.observability.redaction import redact

# structlog's ProcessorFormatter needs these on the record; they aren't log fields.
_STRUCTLOG_INTERNALS = ("_logger", "_name")


class OtlpLogHandler(LoggingHandler):
    """
    Exports each record as the same JSON line stdout gets, redacted like a
    span on its way out (ADR-0002). The record's trace context goes with it,
    so Grafana can link a line to its trace. OpenTelemetry's own records are
    skipped: an export failure would otherwise be exported, and fail again.
    """

    def __init__(self, provider: LoggerProvider, formatter: logging.Formatter):
        super().__init__(logger_provider=provider)
        self.line_formatter = formatter

    def emit(self, record: logging.LogRecord) -> None:
        if record.name.startswith("opentelemetry"):
            return
        super().emit(self._exported(record))

    def _exported(self, record: logging.LogRecord) -> logging.LogRecord:
        """A copy whose message is the rendered line, without structlog's internals."""
        fields = {
            key: value
            for key, value in vars(record).items()
            if key not in _STRUCTLOG_INTERNALS
        }
        exported = logging.makeLogRecord(fields)
        exported.msg = redact(self.line_formatter.format(record))
        # The line already holds any traceback, redacted with the rest of it.
        exported.args, exported.exc_info, exported.exc_text = (), None, None
        return exported
