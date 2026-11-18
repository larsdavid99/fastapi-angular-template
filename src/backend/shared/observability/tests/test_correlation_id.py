"""Tests that every log line emitted during a request carries its correlation ID."""

import io
import json
import logging

import pytest
import structlog
from fastapi import FastAPI, Response
from fastapi.testclient import TestClient
from starlette.types import Message

from shared.observability.correlation_id_middleware import CorrelationIdMiddleware
from shared.observability.internal_error_handler import internal_error_handler
from shared.observability.logging_config import configure_logging


async def _no_receive() -> Message:
    raise AssertionError("the app under test never reads the request body")


async def _discard(message: Message) -> None:
    pass


@pytest.fixture
def log_lines():
    """Route all JSON log output into a buffer; returns a reader of parsed lines."""
    root = logging.getLogger()
    app_handlers, app_level = root.handlers[:], root.level
    buffer = io.StringIO()
    configure_logging(level="INFO", stream=buffer)
    # The TestClient's own httpx logging happens client-side, outside any request.
    client_loggers = [logging.getLogger("httpx")]
    for logger in client_loggers:
        logger.setLevel(logging.WARNING)
    yield lambda: [json.loads(line) for line in buffer.getvalue().splitlines()]
    for logger in client_loggers:
        logger.setLevel(logging.NOTSET)
    # Restore the app's handlers as they were, the log export's included.
    root.handlers, root.level = app_handlers, app_level


def test_incoming_correlation_id_is_echoed_and_on_every_log_line(client, log_lines):
    response = client.get("/health", headers={"X-Correlation-ID": "abc-123"})

    assert response.headers["X-Correlation-ID"] == "abc-123"
    lines = log_lines()
    assert lines, "the request should have produced at least one log line"
    assert {line["correlation_id"] for line in lines} == {"abc-123"}


def test_correlation_id_is_generated_when_absent(client, log_lines):
    response = client.get("/health")

    generated = response.headers["X-Correlation-ID"]
    assert generated
    assert {line["correlation_id"] for line in log_lines()} == {generated}


def test_each_request_gets_its_own_correlation_id(client, log_lines):
    first = client.get("/health").headers["X-Correlation-ID"]
    second = client.get("/health").headers["X-Correlation-ID"]

    assert first != second
    assert {line["correlation_id"] for line in log_lines()} == {first, second}


def test_existing_correlation_id_header_is_replaced_not_duplicated(log_lines):
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/preset")
    def preset(response: Response):
        response.headers["X-Correlation-ID"] = "inner"
        return {}

    response = TestClient(app).get("/preset", headers={"X-Correlation-ID": "outer"})

    assert response.headers.get_list("X-Correlation-ID") == ["outer"]


def test_context_bound_outside_the_request_is_kept(log_lines):
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/traced")
    def traced():
        structlog.get_logger("app").info("traced")
        return {}

    async def outer(scope, receive, send):
        structlog.contextvars.bind_contextvars(trace_id="t-1")
        await app(scope, receive, send)

    TestClient(outer).get("/traced", headers={"X-Correlation-ID": "c-1"})

    events = {line["event"]: line for line in log_lines()}
    assert events["traced"]["trace_id"] == "t-1"
    assert events["traced"]["correlation_id"] == "c-1"


def test_malformed_incoming_correlation_id_is_replaced(client, log_lines):
    response = client.get("/health", headers={"X-Correlation-ID": "bad id\n{}"})

    assert response.headers["X-Correlation-ID"] != "bad id\n{}"


def test_structlog_and_stdlib_lines_inside_a_request_are_json_with_the_id(log_lines):
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/noisy")
    def noisy():
        structlog.get_logger("app").info("from_structlog")
        logging.getLogger("third_party").warning("from_stdlib")
        return {}

    TestClient(app).get("/noisy", headers={"X-Correlation-ID": "xyz"})

    events = {line["event"]: line for line in log_lines()}
    assert events["from_structlog"]["correlation_id"] == "xyz"
    assert events["from_stdlib"]["correlation_id"] == "xyz"
    assert events["from_stdlib"]["level"] == "warning"


def _boom():
    raise RuntimeError("boom")


def _app_with(route, raise_server_exceptions=False):
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)
    app.add_exception_handler(Exception, internal_error_handler)
    app.get("/route")(route)
    return TestClient(app, raise_server_exceptions=raise_server_exceptions)


def test_unhandled_exception_is_logged_and_answered_with_the_id(log_lines):
    response = _app_with(_boom).get("/route", headers={"X-Correlation-ID": "err-1"})

    assert response.status_code == 500
    assert response.headers["X-Correlation-ID"] == "err-1"
    events = {line["event"]: line for line in log_lines()}
    assert events["request.failed"]["correlation_id"] == "err-1"
    assert "RuntimeError: boom" in events["request.failed"]["exception"]
    assert events["request.completed"]["status"] == 500
    assert {line["correlation_id"] for line in log_lines()} == {"err-1"}


def test_unhandled_exception_still_reaches_the_test_client(log_lines):
    client = _app_with(_boom, raise_server_exceptions=True)

    with pytest.raises(RuntimeError, match="boom"):
        client.get("/route")


def test_app_answers_unhandled_exceptions_with_the_id():
    from main import app

    assert app.exception_handlers[Exception] is internal_error_handler


async def test_request_without_a_response_is_logged_as_aborted(log_lines):
    async def never_responds(scope, receive, send):
        return

    middleware = CorrelationIdMiddleware(never_responds)
    scope = {"type": "http", "method": "GET", "path": "/gone", "headers": []}

    await middleware(scope, _no_receive, _discard)

    events = {line["event"]: line for line in log_lines()}
    assert "request.completed" not in events
    assert events["request.aborted"]["path"] == "/gone"


async def test_incoming_id_with_trailing_newline_is_replaced(log_lines):
    async def ok(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    sent = []

    async def capture(message):
        sent.append(message)

    middleware = CorrelationIdMiddleware(ok)
    headers = [(b"x-correlation-id", b"abc\n")]
    scope = {"type": "http", "method": "GET", "path": "/", "headers": headers}

    await middleware(scope, _no_receive, capture)

    echoed = dict(sent[0]["headers"])[b"x-correlation-id"]
    assert echoed != b"abc\n"
