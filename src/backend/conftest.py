"""Shared test fixtures."""

import pytest
from fastapi.testclient import TestClient
from opentelemetry import _logs, trace
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import InMemoryLogRecordExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from main import app
from shared.observability.ai_tracing.ai_trace_dependencies import get_ai_trace_client
from shared.observability.log_export import export_logs
from shared.observability.tests.ai_tracing.fake_ai_trace_client import FakeAiTraceClient
from shared.observability.tracing import export_spans


@pytest.fixture
def ai_traces() -> FakeAiTraceClient:
    """Fake AI Trace Client; inspect the traces that would reach Langfuse."""
    return FakeAiTraceClient()


@pytest.fixture
def client(ai_traces: FakeAiTraceClient):
    """The app, with AI tracing faked so no test can send traces to Langfuse."""
    app.dependency_overrides[get_ai_trace_client] = lambda: ai_traces
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def _span_exporter() -> InMemorySpanExporter:
    """Spans the app exports, through the same redaction as production's."""
    exporter = InMemorySpanExporter()
    provider = trace.get_tracer_provider()
    assert isinstance(provider, TracerProvider), "the app configures tracing"
    export_spans(provider, exporter, batch=False)
    return exporter


@pytest.fixture
def spans(_span_exporter: InMemorySpanExporter) -> InMemorySpanExporter:
    """The spans exported during this test."""
    _span_exporter.clear()
    return _span_exporter


@pytest.fixture(scope="session")
def _log_exporter() -> InMemoryLogRecordExporter:
    """Log lines the app exports, as they'd reach Loki."""
    exporter = InMemoryLogRecordExporter()
    provider = _logs.get_logger_provider()
    assert isinstance(provider, LoggerProvider), "the app configures log export"
    export_logs(provider, exporter, batch=False)
    return exporter


@pytest.fixture
def exported_logs(
    _log_exporter: InMemoryLogRecordExporter,
) -> InMemoryLogRecordExporter:
    """The log lines exported during this test."""
    _log_exporter.clear()
    return _log_exporter
