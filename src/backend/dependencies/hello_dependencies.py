"""Hello Dependencies - DI wiring."""

from typing import Annotated

from fastapi import Depends

from clients.example_http_client import ExampleHttpClient
from facade.hello_facade import HelloFacade
from logic.hello_logic import HelloLogic


def get_example_http_client() -> ExampleHttpClient:
    """Provide an ExampleHttpClient instance."""
    return ExampleHttpClient()


def get_hello_logic(
    example_http_client: Annotated[ExampleHttpClient, Depends(get_example_http_client)],
) -> HelloLogic:
    """Provide a HelloLogic instance with its Client dependency."""
    return HelloLogic(example_http_client)


def get_hello_facade(
    hello_logic: Annotated[HelloLogic, Depends(get_hello_logic)],
) -> HelloFacade:
    """Provide a HelloFacade instance with its Logic dependency."""
    return HelloFacade(hello_logic)
