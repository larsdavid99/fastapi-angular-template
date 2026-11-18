"""OpenTelemetry traces of inbound requests (ADR-0002)."""

import structlog
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.trace import SpanKind

PHONE = "+46701234567"
SECRET = "vendor-api-key"
# The URL-encoded "+" is how a phone number arrives in a query string.
LEAKY_URL = f"/health?api_key={SECRET}&phone=%2B{PHONE[1:]}"


def _get(client, path: str = "/health", correlation_id: str = "trace-1") -> None:
    response = client.get(path, headers={"X-Correlation-ID": correlation_id})
    assert response.status_code == 200


def _server_span(spans: list[ReadableSpan]) -> ReadableSpan:
    [server] = [span for span in spans if span.kind == SpanKind.SERVER]
    return server


def _everything_exported(spans: list[ReadableSpan]) -> str:
    return "\n".join(span.to_json() for span in spans)


def test_a_request_is_traced(client, spans):
    _get(client)

    server = _server_span(spans.get_finished_spans())
    assert server.name == "GET /health"


def test_every_span_carries_the_correlation_id(client, spans):
    _get(client, correlation_id="request-7")

    exported = spans.get_finished_spans()
    assert exported
    for span in exported:
        assert (span.attributes or {}).get("correlation_id") == "request-7", span.name


def test_traces_hold_no_phone_numbers_or_query_string_secrets(client, spans):
    _get(client, LEAKY_URL)

    exported = _everything_exported(spans.get_finished_spans())
    assert "/health" in exported
    assert PHONE[1:] not in exported
    assert SECRET not in exported


def test_log_lines_carry_the_trace_id_of_their_request(client, spans):
    with structlog.testing.capture_logs(
        processors=[structlog.contextvars.merge_contextvars]
    ) as logs:
        _get(client)

    server = _server_span(spans.get_finished_spans())
    assert server.context is not None
    trace_id = format(server.context.trace_id, "032x")
    completed = [log for log in logs if log["event"] == "request.completed"]
    assert completed and all(log["trace_id"] == trace_id for log in completed)
