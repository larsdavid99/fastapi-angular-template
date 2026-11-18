"""Hello Logic — business rules for the hello feature."""

from modules.hello.logic.uuid_source import UuidSource
from modules.hello.models.dtos.hello_request import HelloRequest
from modules.hello.models.dtos.hello_response import HelloResponse


class HelloLogic:
    """Composes the greeting and attaches a UUID from its UuidSource."""

    def __init__(self, uuid_source: UuidSource):
        self.uuid_source = uuid_source

    async def greet(self, request: HelloRequest) -> HelloResponse:
        """Build a greeting message and attach a fresh UUID."""
        uuid = await self.uuid_source.next_uuid()
        message = self._build_message(request.name)
        return HelloResponse(message=message, uuid=uuid)

    def _build_message(self, name: str) -> str:
        return f"Hello {name}"
