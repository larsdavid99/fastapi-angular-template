"""Hello Logic — business rules and orchestration for the hello feature."""

import logging

from clients.example_http_client import ExampleHttpClient
from models.dtos.hello_request import HelloRequest
from models.dtos.hello_response import HelloResponse

logger = logging.getLogger(__name__)


class HelloLogic:
    """Composes the greeting and orchestrates the example HTTP call."""

    def __init__(self, example_http_client: ExampleHttpClient):
        self.example_http_client = example_http_client

    async def greet(self, request: HelloRequest) -> HelloResponse:
        """Build a greeting message and attach a fetched UUID."""
        uuid = await self.example_http_client.fetch_uuid()
        message = self._build_message(request.name)
        return HelloResponse(message=message, uuid=uuid)

    def _build_message(self, name: str) -> str:
        return f"Hello {name}"
