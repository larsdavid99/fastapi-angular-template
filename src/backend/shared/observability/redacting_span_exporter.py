"""Redacting Span Exporter — no secrets, phone numbers or positions leave in traces."""

from collections.abc import Mapping, Sequence

from opentelemetry.sdk.trace import Event, ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace import Status
from opentelemetry.util.types import AnyValue, Attributes

from shared.observability.redaction import redact as _redact


class RedactingSpanExporter(SpanExporter):
    """
    Wraps the real exporter and cleans every span on its way out: its name,
    attributes, events (including recorded exceptions) and status message.
    This catches what instrumentation records on its own, such as URLs.
    Message text never needs catching here: nothing records request or
    response bodies, and the database engine hides statement parameters.
    """

    def __init__(self, exporter: SpanExporter):
        self.exporter = exporter

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        return self.exporter.export([self._redacted(span) for span in spans])

    def shutdown(self) -> None:
        self.exporter.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return self.exporter.force_flush(timeout_millis)

    def _redacted(self, span: ReadableSpan) -> ReadableSpan:
        return ReadableSpan(
            name=_redact(span.name),
            context=span.context,
            parent=span.parent,
            resource=span.resource,
            attributes=self._attributes(span.attributes),
            events=[self._event(event) for event in span.events],
            links=span.links,
            kind=span.kind,
            status=Status(
                span.status.status_code,
                span.status.description and _redact(span.status.description),
            ),
            start_time=span.start_time,
            end_time=span.end_time,
            instrumentation_scope=span.instrumentation_scope,
        )

    def _event(self, event: Event) -> Event:
        return Event(
            _redact(event.name), self._attributes(event.attributes), event.timestamp
        )

    def _attributes(self, attributes: Attributes) -> Attributes:
        if attributes is None:
            return None
        return {key: self._value(value) for key, value in attributes.items()}

    def _value(self, value: AnyValue) -> AnyValue:
        if isinstance(value, str):
            return _redact(value)
        if isinstance(value, Sequence) and not isinstance(value, bytes):
            return [self._value(item) for item in value]
        if isinstance(value, Mapping):
            return {key: self._value(item) for key, item in value.items()}
        return value
