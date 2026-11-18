"""Hello Dependencies — DI wiring; the only place the UuidSource adapter is chosen."""

from collections.abc import AsyncIterator
from typing import Annotated

import httpx
from fastapi import Depends

from modules.hello.clients.httpbin_uuid_source import HttpbinUuidSource
from modules.hello.facade.hello_facade import HelloFacade
from modules.hello.logic.hello_logic import HelloLogic
from modules.hello.logic.uuid_source import UuidSource


async def get_uuid_source() -> AsyncIterator[UuidSource]:
    """An httpbin-backed UuidSource whose HTTP client closes after the request."""
    async with httpx.AsyncClient(
        base_url=HttpbinUuidSource.BASE_URL, timeout=10.0
    ) as http:
        yield HttpbinUuidSource(http)


def get_hello_logic(
    uuid_source: Annotated[UuidSource, Depends(get_uuid_source)],
) -> HelloLogic:
    return HelloLogic(uuid_source)


def get_hello_facade(
    hello_logic: Annotated[HelloLogic, Depends(get_hello_logic)],
) -> HelloFacade:
    return HelloFacade(hello_logic)
