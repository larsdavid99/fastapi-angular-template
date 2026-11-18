"""Example HTTP Client — pure HTTP communication with httpbin.org."""

import httpx
import structlog

from exceptions.example_api_error import ExampleApiError

logger = structlog.get_logger(__name__)


class ExampleHttpClient:
    """
    Pure HTTP client example.

    Demonstrates the Client layer pattern: no business logic,
    only request/response and error wrapping.
    """

    UUID_URL = "https://httpbin.org/uuid"

    def __init__(self, timeout: float = 10.0, uuid_url: str = UUID_URL):
        self._timeout = timeout
        self._uuid_url = uuid_url

    async def fetch_uuid(self) -> str:
        """
        GET https://httpbin.org/uuid and return the uuid string.

        Raises:
            ExampleApiError: If the request fails.
        """
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.get(self._uuid_url)
                response.raise_for_status()
            except httpx.HTTPError as e:
                raise ExampleApiError(
                    message=f"Failed to fetch uuid: {e}",
                    source="httpbin",
                )

        data = response.json()
        uuid = data.get("uuid")
        if not uuid:
            raise ExampleApiError(
                message="Response missing 'uuid' field",
                source="httpbin",
            )
        return uuid
