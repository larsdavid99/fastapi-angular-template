"""Hello Facade — coordinates Logic classes for the hello workflow."""

import structlog

from logic.hello_logic import HelloLogic
from models.dtos.hello_request import HelloRequest
from models.dtos.hello_response import HelloResponse

logger = structlog.get_logger(__name__)


class HelloFacade:
    """Single Logic in this template; more would be coordinated here."""

    def __init__(self, hello_logic: HelloLogic):
        self.hello_logic = hello_logic

    async def greet(self, request: HelloRequest) -> HelloResponse:
        return await self.hello_logic.greet(request)
