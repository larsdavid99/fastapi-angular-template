"""Hello Router."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from dependencies.hello_dependencies import get_hello_facade
from exceptions.example_api_error import ExampleApiError
from facade.hello_facade import HelloFacade
from models.dtos.hello_request import HelloRequest
from models.dtos.hello_response import HelloResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["hello"])


@router.post("/hello", response_model=HelloResponse)
async def hello(
    request: HelloRequest,
    facade: Annotated[HelloFacade, Depends(get_hello_facade)],
) -> HelloResponse:
    """Return a greeting plus a UUID fetched from an external API."""
    try:
        return await facade.greet(request)
    except ExampleApiError as e:
        logger.warning(f"Example API error: {e}")
        raise HTTPException(status_code=502, detail=e.message)
