"""Outbound httpx calls are traced without their query strings (ADR-0002)."""

import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import structlog
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.trace import SpanKind

from clients.example_http_client import ExampleHttpClient

SECRET = "vendor-api-key"
PHONE = "+46701112233"


class _Vendor(BaseHTTPRequestHandler):
    """A real HTTP server: tracing hooks the real transport, not a mock one."""

    def do_GET(self) -> None:
        body = json.dumps({"uuid": "uuid-1"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture
def vendor_url() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Vendor)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def _client_spans(spans) -> list[ReadableSpan]:
    exported = [s for s in spans.get_finished_spans() if s.kind == SpanKind.CLIENT]
    assert exported, "the outbound call should be traced"
    return exported


def _exported(spans) -> str:
    return "\n".join(span.to_json() for span in _client_spans(spans))


async def test_an_outbound_call_is_traced_without_its_query_string(vendor_url, spans):
    client = ExampleHttpClient(uuid_url=f"{vendor_url}/uuid?api_key={SECRET}")

    assert await client.fetch_uuid() == "uuid-1"

    exported = _exported(spans)
    assert "/uuid" in exported
    assert SECRET not in exported


async def test_a_phone_number_in_an_outbound_url_is_masked(vendor_url, spans):
    client = ExampleHttpClient(uuid_url=f"{vendor_url}/contacts/{PHONE}/uuid")

    await client.fetch_uuid()

    exported = _exported(spans)
    assert "/contacts/" in exported
    assert PHONE[1:] not in exported
    assert PHONE[-2:] in exported  # masked, not dropped: the tail still helps


async def test_an_outbound_call_carries_the_correlation_id(vendor_url, spans):
    client = ExampleHttpClient(uuid_url=f"{vendor_url}/uuid")

    with structlog.contextvars.bound_contextvars(correlation_id="request-7"):
        await client.fetch_uuid()

    for span in _client_spans(spans):
        assert (span.attributes or {}).get("correlation_id") == "request-7"
