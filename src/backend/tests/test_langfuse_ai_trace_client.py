"""Seam 3: what the Langfuse AI Trace Client exports (captured before the network)."""

import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from langfuse import LangfuseOtelSpanAttributes as Langfuse
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from clients.langfuse_ai_trace_client import LangfuseAiTraceClient
from models.dtos.ai_trace import AiTrace
from models.dtos.langfuse_config import LangfuseConfig

STARTED = datetime(2026, 10, 18, 21, 0, tzinfo=timezone.utc)
TRACE = AiTrace(
    name="summarise",
    correlation_id="request-1",
    model="claude-haiku-5-5",
    prompt_version="summarise-v2",
    input='{"text": "Call <NAME_1> on <PHONE_1>"}',
    output='{"summary": "Call <NAME_1>", "people": [{"name": "<NAME_1>"}]}',
    input_tokens=412,
    output_tokens=87,
    cost_usd=0.0000847,
    started_at=STARTED,
    latency_ms=840,
)


@pytest.fixture
def exporter() -> InMemorySpanExporter:
    return InMemorySpanExporter()


@pytest.fixture
def langfuse(exporter):
    client = LangfuseAiTraceClient(
        LangfuseConfig(
            # Langfuse keeps one set of resources per key and process.
            public_key=f"pk-lf-{uuid.uuid4()}",
            secret_key="sk-lf-test",
            base_url="http://langfuse.invalid",
            environment="test",
        ),
        span_exporter=exporter,
    )
    yield client
    client.shutdown()


def _exported(langfuse, exporter, ai_trace: AiTrace = TRACE):
    langfuse.record(ai_trace)
    langfuse.flush()
    [span] = exporter.get_finished_spans()
    return span


def test_an_ai_call_is_exported_as_a_generation(langfuse, exporter):
    span = _exported(langfuse, exporter)

    attributes = span.attributes or {}
    assert span.name == "summarise"
    assert attributes[Langfuse.OBSERVATION_TYPE] == "generation"
    assert attributes[Langfuse.OBSERVATION_MODEL] == "claude-haiku-5-5"
    assert attributes[Langfuse.VERSION] == "summarise-v2"
    prompt_version = f"{Langfuse.OBSERVATION_METADATA}.prompt_version"
    assert json.loads(str(attributes[prompt_version])) == "summarise-v2"
    assert attributes[Langfuse.OBSERVATION_INPUT] == TRACE.input
    assert attributes[Langfuse.OBSERVATION_OUTPUT] == TRACE.output
    assert attributes[Langfuse.ENVIRONMENT] == "test"


def test_tokens_and_cost_are_exported(langfuse, exporter):
    attributes = _exported(langfuse, exporter).attributes or {}

    usage = json.loads(str(attributes[Langfuse.OBSERVATION_USAGE_DETAILS]))
    cost = json.loads(str(attributes[Langfuse.OBSERVATION_COST_DETAILS]))
    assert usage == {"input": 412, "output": 87}
    assert cost == {"total": pytest.approx(0.0000847)}


def test_the_generation_spans_the_call_so_langfuse_shows_its_latency(
    langfuse, exporter
):
    span = _exported(langfuse, exporter)

    assert span.start_time == int(STARTED.timestamp() * 1e9)
    assert span.end_time is not None
    assert timedelta(microseconds=(span.end_time - span.start_time) / 1000) == (
        timedelta(milliseconds=840)
    )


def test_the_correlation_id_is_on_the_trace_and_the_generation(langfuse, exporter):
    attributes = _exported(langfuse, exporter).attributes or {}

    for prefix in (Langfuse.TRACE_METADATA, Langfuse.OBSERVATION_METADATA):
        assert json.loads(str(attributes[f"{prefix}.correlation_id"])) == ("request-1")
    assert attributes[Langfuse.TRACE_NAME] == "summarise"


def test_a_failed_call_is_exported_as_an_error(langfuse, exporter):
    failed = TRACE.model_copy(
        update={
            "output": None,
            "input_tokens": None,
            "output_tokens": None,
            "cost_usd": None,
            "error": "AI unreachable",
        }
    )

    attributes = _exported(langfuse, exporter, failed).attributes or {}

    assert attributes[Langfuse.OBSERVATION_LEVEL] == "ERROR"
    assert attributes[Langfuse.OBSERVATION_STATUS_MESSAGE] == "AI unreachable"
    assert Langfuse.OBSERVATION_OUTPUT not in attributes
    assert Langfuse.OBSERVATION_USAGE_DETAILS not in attributes
    assert Langfuse.OBSERVATION_COST_DETAILS not in attributes


def test_each_ai_call_is_its_own_langfuse_trace_even_inside_a_request(
    langfuse, exporter
):
    # The app's request span lives in another provider and never reaches
    # Langfuse, so a generation parented to it would be orphaned there.
    request_tracer = TracerProvider().get_tracer("app")
    with request_tracer.start_as_current_span("POST /api/hello"):
        span = _exported(langfuse, exporter)

    assert span.parent is None
    assert span.context is not None
    assert span.context.trace_id != trace.INVALID_TRACE_ID
