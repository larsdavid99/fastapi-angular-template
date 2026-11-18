"""Request Context DTO."""

from pydantic import BaseModel, Field


class RequestContext(BaseModel):
    """What CorrelationIdMiddleware tracks about one inbound HTTP request."""

    correlation_id: str = Field(..., description="ID bound to every log line")
    method: str
    path: str
    started: float = Field(..., description="time.perf_counter() at arrival")
    status: int | None = Field(None, description="Set once the response starts")
