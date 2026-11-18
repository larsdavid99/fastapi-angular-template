"""Hello Facade — the hello module's public API, one method per use case."""

from modules.hello.logic.hello_logic import HelloLogic
from modules.hello.models.dtos.hello_request import HelloRequest
from modules.hello.models.dtos.hello_response import HelloResponse


class HelloFacade:
    """Single Logic in this template; more would be coordinated here."""

    def __init__(self, hello_logic: HelloLogic):
        self.hello_logic = hello_logic

    async def greet(self, request: HelloRequest) -> HelloResponse:
        return await self.hello_logic.greet(request)
