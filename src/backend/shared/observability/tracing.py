"""OpenTelemetry tracing for inbound requests and outbound calls (ADR-0002)."""

import httpx
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor, RequestInfo
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SimpleSpanProcessor,
    SpanExporter,
)

from shared.observability.correlation_id_span_processor import (
    CorrelationIdSpanProcessor,
)
from shared.observability.otlp_settings import otlp_headers, otlp_resource, otlp_url
from shared.observability.redacting_span_exporter import RedactingSpanExporter
from shared.config.settings import Settings


def configure_tracing(settings: Settings) -> TracerProvider:
    """
    The app's tracer provider. Spans are exported over OTLP/HTTP when an
    endpoint is configured (grafana/otel-lgtm locally, e.g. Grafana Cloud
    when deployed), so changing the backend is configuration, not code.
    """
    provider = TracerProvider(resource=otlp_resource(settings))
    provider.add_span_processor(CorrelationIdSpanProcessor())
    if settings.otel_exporter_otlp_endpoint:
        export_spans(provider, _otlp_exporter(settings))
    trace.set_tracer_provider(provider)
    return provider


def export_spans(
    provider: TracerProvider, exporter: SpanExporter, batch: bool = True
) -> None:
    """Every exporter gets redacted spans; batch=False exports as spans end."""
    redacting = RedactingSpanExporter(exporter)
    processor = (
        BatchSpanProcessor(redacting) if batch else SimpleSpanProcessor(redacting)
    )
    provider.add_span_processor(processor)


def instrument(app: FastAPI, provider: TracerProvider) -> None:
    """
    Trace requests and every httpx call. Request and response bodies are never
    recorded, nor is an httpx call's query string. Once the app has a database,
    add opentelemetry-instrumentation-sqlalchemy here (instrument the engine).
    """
    FastAPIInstrumentor.instrument_app(
        app, tracer_provider=provider, exclude_spans=["receive", "send"]
    )
    HTTPXClientInstrumentor().instrument(
        tracer_provider=provider, request_hook=_url_without_query
    )


# Where httpx's spans keep the URL, under the old and the new conventions.
_URL_ATTRIBUTES = ("http.url", "url.full")


def _url_without_query(span: trace.Span, request: RequestInfo) -> None:
    """
    Query strings carry secrets and personal data, so the span never holds
    them; redaction is a backstop (ADR-0002).
    """
    if not isinstance(span, ReadableSpan) or span.attributes is None:
        return
    if not isinstance(request.url, httpx.URL):
        return  # a raw tuple only comes from an httpx older than ours
    url = str(request.url.copy_with(query=None))
    for attribute in _URL_ATTRIBUTES:
        if attribute in span.attributes:
            span.set_attribute(attribute, url)


def _otlp_exporter(settings: Settings) -> OTLPSpanExporter:
    return OTLPSpanExporter(
        endpoint=otlp_url(settings, "traces"), headers=otlp_headers(settings)
    )
