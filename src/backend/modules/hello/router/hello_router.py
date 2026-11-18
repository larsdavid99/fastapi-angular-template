"""Hello Router."""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException

from modules.hello.dependencies.hello_dependencies import get_hello_facade
from modules.hello.exceptions.uuid_source_unavailable_error import (
    UuidSourceUnavailableError,
)
from modules.hello.facade.hello_facade import HelloFacade
from modules.hello.models.dtos.hello_request import HelloRequest
from modules.hello.models.dtos.hello_response import HelloResponse

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api", tags=["hello"])


@router.post("/hello", response_model=HelloResponse)
async def hello(
    request: HelloRequest,
    facade: Annotated[HelloFacade, Depends(get_hello_facade)],
) -> HelloResponse:
    """Return a greeting plus a fresh UUID."""
    try:
        return await facade.greet(request)
    except UuidSourceUnavailableError as e:
        logger.warning("hello.upstream_failed")
        raise HTTPException(status_code=502, detail=e.message)
