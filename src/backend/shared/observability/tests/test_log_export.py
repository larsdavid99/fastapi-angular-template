"""Log lines exported over OpenTelemetry, for Loki (ADR-0002)."""

import json
import logging
from typing import Any

from opentelemetry.sdk._logs import ReadableLogRecord
from opentelemetry.trace import SpanKind

PHONE = "+46701234567"
SECRET = "vendor-api-key"
LEAKY_URL = f"/health?api_key={SECRET}"


def _get(client, path: str = "/health", correlation_id: str = "logs-1") -> None:
    response = client.get(path, headers={"X-Correlation-ID": correlation_id})
    assert response.status_code == 200


def _lines(exported_logs) -> list[dict[str, Any]]:
    return [
        json.loads(str(record.log_record.body)) for record in _records(exported_logs)
    ]


def _records(exported_logs) -> list[ReadableLogRecord]:
    return list(exported_logs.get_finished_logs())


def _everything_exported(exported_logs) -> str:
    return "\n".join(record.to_json() for record in _records(exported_logs))


def test_each_log_line_is_exported_as_the_json_stdout_gets(client, exported_logs):
    _get(client, correlation_id="request-7")

    completed = [
        line for line in _lines(exported_logs) if line["event"] == "request.completed"
    ]
    assert completed
    assert all(line["correlation_id"] == "request-7" for line in completed)
    assert all(line["level"] == "info" for line in completed)


def test_an_exported_line_carries_its_request_s_trace(client, spans, exported_logs):
    _get(client)

    [server] = [s for s in spans.get_finished_spans() if s.kind == SpanKind.SERVER]
    assert server.context is not None
    [completed] = [
        record
        for record in _records(exported_logs)
        if '"request.completed"' in str(record.log_record.body)
    ]
    assert completed.log_record.trace_id == server.context.trace_id


def test_exported_lines_hold_no_phone_numbers_or_query_string_secrets(exported_logs):
    # As a stdlib logger such as uvicorn's might, when a request fails.
    logging.getLogger("uvicorn.error").error("failed GET %s from %s", LEAKY_URL, PHONE)

    exported = _everything_exported(exported_logs)
    assert "uvicorn.error" in exported
    assert PHONE not in exported and PHONE[1:] not in exported
    assert PHONE[-2:] in exported  # masked, not dropped: the tail still helps
    assert SECRET not in exported


def test_structlog_s_internals_are_not_exported(client, exported_logs):
    _get(client)

    for record in _records(exported_logs):
        attributes = record.log_record.attributes or {}
        assert "_logger" not in attributes and "_name" not in attributes


def test_opentelemetry_s_own_log_lines_are_not_exported(exported_logs):
    logging.getLogger("opentelemetry.exporter.otlp").warning("export failed")

    assert _records(exported_logs) == []


def test_numbers_that_arent_phone_numbers_are_exported_as_they_are(exported_logs):
    logging.getLogger("uvicorn.error").error("took 12.5 ms, order 1234567")

    assert "took 12.5 ms, order 1234567" in _everything_exported(exported_logs)
