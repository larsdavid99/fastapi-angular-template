"""HttpbinUuidSource against a fake transport: httpbin's shape and errors stop here."""

import httpx
import pytest

from modules.hello.clients.httpbin_uuid_source import HttpbinUuidSource
from modules.hello.exceptions.uuid_source_unavailable_error import (
    UuidSourceUnavailableError,
)


def _source(handler) -> HttpbinUuidSource:
    http = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://httpbin.test"
    )
    return HttpbinUuidSource(http)


async def test_returns_the_uuid_from_httpbin():
    source = _source(lambda request: httpx.Response(200, json={"uuid": "uuid-1"}))

    assert await source.next_uuid() == "uuid-1"


async def test_a_server_error_becomes_unavailable():
    source = _source(lambda request: httpx.Response(503))

    with pytest.raises(UuidSourceUnavailableError) as raised:
        await source.next_uuid()

    assert "httpbin" not in raised.value.message


async def test_a_network_error_becomes_unavailable():
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(UuidSourceUnavailableError):
        await _source(refuse).next_uuid()


async def test_a_response_without_a_uuid_becomes_unavailable():
    source = _source(lambda request: httpx.Response(200, json={}))

    with pytest.raises(UuidSourceUnavailableError):
        await source.next_uuid()
