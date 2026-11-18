"""Httpbin UUID Source — the UuidSource adapter for httpbin.org."""

import httpx

from modules.hello.exceptions.uuid_source_unavailable_error import (
    UuidSourceUnavailableError,
)


class HttpbinUuidSource:
    """
    Implements UuidSource. Thin: one GET, and httpbin's errors and response
    shape stop here.
    """

    BASE_URL = "https://httpbin.org"

    def __init__(self, http: httpx.AsyncClient):
        self.http = http

    async def next_uuid(self) -> str:
        try:
            response = await self.http.get("/uuid")
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise UuidSourceUnavailableError() from e
        return self._uuid(response.json())

    def _uuid(self, body: dict) -> str:
        uuid = body.get("uuid")
        if not uuid:
            raise UuidSourceUnavailableError("UUID source answered without a uuid")
        return uuid
